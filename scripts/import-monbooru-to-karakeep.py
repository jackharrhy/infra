#!/usr/bin/env python3
"""Idempotently import supported Monbooru gallery files into Karakeep.

Usage:
  KARAKEEP_API_KEY=... python3 scripts/import-monbooru-to-karakeep.py --dry-run
  KARAKEEP_API_KEY=... python3 scripts/import-monbooru-to-karakeep.py

The manifest is updated atomically after every remote write, so a failed run can
resume without re-uploading successfully recorded assets. Video files are left
in the source archive because Karakeep's asset-bookmark API supports images/PDFs.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

API_BASE = "https://karakeep.jackharrhy.dev/api/v1"
SOURCE_DB = Path("/mnt/terrabud/docker-data/newport/monbooru/data/default/monbooru.db")
SOURCE_GALLERY = Path("/mnt/terrabud/docker-data/newport/monbooru/gallery")
MANIFEST_PATH = Path("/mnt/terrabud/docker-data/newport/karakeep/imports/monbooru-20260904.json")
SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="validate the source only")
    return parser.parse_args()


def source_rows() -> list[dict[str, object]]:
    db = sqlite3.connect(f"file:{SOURCE_DB}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    try:
        rows = db.execute(
            """
            SELECT
              i.id, i.canonical_path, i.file_type, i.file_size, i.source,
              i.url, i.note, i.ingested_at,
              group_concat(s.url, '\n') AS source_urls
            FROM images AS i
            LEFT JOIN image_sources AS s ON s.image_id = i.id
            GROUP BY i.id
            ORDER BY i.id
            """
        ).fetchall()
    finally:
        db.close()

    records: list[dict[str, object]] = []
    for row in rows:
        data = dict(row)
        canonical = Path(str(data["canonical_path"]))
        data["file_name"] = canonical.name
        data["local_path"] = str(SOURCE_GALLERY / canonical.name)
        urls = [u for u in str(data["source_urls"] or "").split("\n") if u]
        data["source_url"] = data["url"] or (urls[0] if urls else None)
        records.append(data)
    return records


def load_manifest() -> dict[str, object]:
    if not MANIFEST_PATH.exists():
        return {"version": 1, "created_at": datetime.now(timezone.utc).isoformat(), "items": {}}
    return json.loads(MANIFEST_PATH.read_text())


def save_manifest(manifest: dict[str, object]) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp = MANIFEST_PATH.with_suffix(".tmp")
    temp.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    temp.replace(MANIFEST_PATH)


def api_request(api_key: str, method: str, path: str, body: bytes | None, headers: dict[str, str]) -> dict[str, object]:
    request = Request(
        API_BASE + path,
        data=body,
        method=method,
        headers={"Authorization": f"Bearer {api_key}", **headers},
    )
    try:
        with urlopen(request, timeout=60) as response:
            payload = response.read()
            if not payload:
                return {}
            return json.loads(payload)
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:1000]
        raise RuntimeError(f"{method} {path} returned HTTP {exc.code}: {detail}") from exc


def upload_asset(api_key: str, local_path: Path) -> str:
    boundary = "----karakeep-monbooru-" + uuid.uuid4().hex
    content_type = mimetypes.guess_type(local_path.name)[0] or "application/octet-stream"
    file_bytes = local_path.read_bytes()
    body = b"".join(
        [
            f"--{boundary}\r\n".encode(),
            (
                f'Content-Disposition: form-data; name="file"; filename="{local_path.name}"\r\n'
                f"Content-Type: {content_type}\r\n\r\n"
            ).encode(),
            file_bytes,
            f"\r\n--{boundary}--\r\n".encode(),
        ]
    )
    result = api_request(
        api_key,
        "POST",
        "/assets",
        body,
        {"Content-Type": f"multipart/form-data; boundary={boundary}", "Accept": "application/json"},
    )
    asset_id = result.get("assetId")
    if not isinstance(asset_id, str) or not asset_id:
        raise RuntimeError("asset upload returned no assetId")
    return asset_id


def create_bookmark(api_key: str, row: dict[str, object], asset_id: str) -> str:
    source_url = row["source_url"]
    payload: dict[str, object] = {
        "type": "asset",
        "assetType": "image",
        "assetId": asset_id,
        "fileName": row["file_name"],
        "title": Path(str(row["file_name"])).stem,
        "createdAt": row["ingested_at"],
        "source": "import",
    }
    if source_url:
        payload["sourceUrl"] = source_url
    if row["note"]:
        payload["note"] = row["note"]
    result = api_request(
        api_key,
        "POST",
        "/bookmarks",
        json.dumps(payload).encode(),
        {"Content-Type": "application/json", "Accept": "application/json"},
    )
    bookmark_id = result.get("id")
    if not isinstance(bookmark_id, str) or not bookmark_id:
        raise RuntimeError("bookmark creation returned no id")
    return bookmark_id


def main() -> int:
    args = parse_args()
    api_key = os.environ.get("KARAKEEP_API_KEY", "")
    if not args.dry_run and not api_key:
        raise SystemExit("KARAKEEP_API_KEY is required unless --dry-run is used")
    if not SOURCE_DB.is_file() or not SOURCE_GALLERY.is_dir():
        raise SystemExit("Monbooru source database or gallery directory is unavailable")

    rows = source_rows()
    supported = [row for row in rows if Path(str(row["file_name"])).suffix.lower() in SUPPORTED_EXTENSIONS]
    skipped = [row for row in rows if row not in supported]
    for row in supported:
        path = Path(str(row["local_path"]))
        if not path.is_file():
            raise SystemExit(f"source file missing: {path}")

    print(f"source_images={len(rows)} supported_images={len(supported)} skipped={len(skipped)}")
    for row in skipped:
        print(f"skip id={row['id']} file={row['file_name']} reason=unsupported_asset_type")
    if args.dry_run:
        return 0

    manifest = load_manifest()
    items = manifest.setdefault("items", {})
    if not isinstance(items, dict):
        raise SystemExit("invalid manifest items")

    for row in supported:
        key = str(row["id"])
        state = items.setdefault(key, {"source": row})
        if not isinstance(state, dict):
            raise SystemExit(f"invalid manifest item {key}")
        asset_id = state.get("asset_id")
        if not isinstance(asset_id, str):
            asset_id = upload_asset(api_key, Path(str(row["local_path"])))
            state["asset_id"] = asset_id
            state["uploaded_at"] = datetime.now(timezone.utc).isoformat()
            save_manifest(manifest)
            print(f"uploaded id={key} file={row['file_name']}")
        bookmark_id = state.get("bookmark_id")
        if not isinstance(bookmark_id, str):
            bookmark_id = create_bookmark(api_key, row, asset_id)
            state["bookmark_id"] = bookmark_id
            state["bookmarked_at"] = datetime.now(timezone.utc).isoformat()
            save_manifest(manifest)
            print(f"created id={key} bookmark={bookmark_id}")
        else:
            print(f"already-imported id={key} bookmark={bookmark_id}")

    manifest["completed_at"] = datetime.now(timezone.utc).isoformat()
    save_manifest(manifest)
    print(f"completed_imports={len(supported)} manifest={MANIFEST_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
