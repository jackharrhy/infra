"""Publish a Tea Garden content snapshot without deploying application code."""

import argparse
import hashlib
import io
import json
from pathlib import Path
from pathlib import PurePosixPath
import re
import shlex
import subprocess
import tarfile
import urllib.parse
import urllib.request

import yaml


def digest(data):
    return hashlib.sha256(data).hexdigest()


def checked_file(root, item):
    relative = item["sourcePath"]
    name = PurePosixPath(relative)
    if name.is_absolute() or ".." in name.parts or "\\" in relative:
        raise ValueError(f"Invalid snapshot path: {relative}")
    target = (root / relative).resolve()
    if (root / relative).is_symlink() or not target.is_relative_to(root.resolve()) or not target.is_file():
        raise ValueError(f"Invalid snapshot path: {relative}")
    data = target.read_bytes()
    if digest(data) != item["hash"] or len(data) != item["bytes"]:
        raise ValueError(f"Hash/size mismatch: {relative}")
    return data


def validate_snapshot(snapshot, assets):
    manifest = json.loads((snapshot / "deploy-manifest.json").read_text())
    sources = set()
    for item in manifest["pages"]:
        source = checked_file(snapshot, item).decode("utf-8")
        frontmatter = re.match(r"^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)", source)
        if not frontmatter:
            raise ValueError(f"Missing frontmatter: {item['sourcePath']}")
        data = yaml.safe_load(frontmatter.group(1))
        if not isinstance(data, dict) or data.get("public") is not True:
            raise ValueError(f"Non-public note: {item['sourcePath']}")
        if item["sourcePath"] in sources:
            raise ValueError("Duplicate source path")
        sources.add(item["sourcePath"])
    if sources != {p.relative_to(snapshot).as_posix() for p in snapshot.rglob("*.md")}:
        raise ValueError("Snapshot contains unlisted notes")
    for item in manifest["assets"]:
        checked_file(assets, item)
    return manifest


def changes(before, after, key):
    old = {item[key]: item for item in before}
    new = {item[key]: item for item in after}
    return {
        "added": sorted(new.keys() - old.keys()),
        "changed": sorted(k for k in new.keys() & old.keys() if new[k]["hash"] != old[k]["hash"]),
        "removed": sorted(old.keys() - new.keys()),
    }


def ssh(command, **kwargs):
    return subprocess.run(
        ["ssh", "-o", "StrictHostKeyChecking=yes", "-o", "HostKeyAlias=mug", "jack@mug", command],
        check=True,
        **kwargs,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--assets", required=True, type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    manifest = validate_snapshot(args.snapshot, args.assets)
    with urllib.request.urlopen("https://jackharrhy.com/deploy-manifest.json", timeout=15) as response:
        previous = json.load(response)
    pages = changes(previous["pages"], manifest["pages"], "sourcePath")
    media = changes(previous["assets"], manifest["assets"], "sourcePath")
    print(json.dumps({"pages": pages, "assets": media}, indent=2))
    print("Removed media will remain in R2; no bucket objects are deleted.")
    if args.dry_run:
        return
    if input("Publish these pages and referenced assets? [y/N] ").lower() not in ("y", "yes"):
        raise SystemExit("Cancelled")

    upload = set(media["added"] + media["changed"])
    for item in manifest["assets"]:
        if item["sourcePath"] not in upload:
            continue
        relative = item["sourcePath"]
        subprocess.run(["rclone", "copyto", str(args.assets / relative), f"jacks-garden:jacks-garden/{relative}"], check=True)
        url = "https://garden.jack.camera/" + urllib.parse.quote(relative, safe="/") + "?v=" + item["hash"]
        with urllib.request.urlopen(url, timeout=120) as response:
            remote = hashlib.file_digest(response, "sha256").hexdigest()
        if remote != item["hash"]:
            raise ValueError(f"CDN readback mismatch: {relative}")

    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for item in manifest["pages"]:
            archive.add(args.snapshot / item["sourcePath"], arcname=item["sourcePath"], recursive=False)
        archive.add(args.snapshot / "deploy-manifest.json", arcname="deploy-manifest.json", recursive=False)
    release = "releases/" + digest((args.snapshot / "deploy-manifest.json").read_bytes())[:16]
    root = "~/infra/hosts/mug/volumes/garden-content"
    ssh(f"mkdir -p {root}/releases && mkdir {root}/{release} && tar -xzf - -C {root}/{release}", input=buffer.getvalue())
    activate = r'''
import os, pathlib, subprocess, time
root = pathlib.Path.home() / "infra/hosts/mug/volumes/garden-content"
current = root / "current"
old = os.readlink(current)
def point(target):
    temporary = root / "current.next"
    temporary.symlink_to(target)
    temporary.replace(current)
def restart():
    subprocess.run(["docker", "compose", "restart", "jackharrhy"], cwd=root.parent.parent, check=True)
point(RELEASE)
try:
    restart()
    for attempt in range(30):
        check = subprocess.run(["docker", "compose", "exec", "-T", "jackharrhy", "node", "--input-type=module", "-e", "const r=await fetch('http://127.0.0.1:4322/healthz');if(!r.ok)process.exit(1)"], cwd=root.parent.parent, capture_output=True)
        if check.returncode == 0:
            print("Activated", RELEASE, "previous", old)
            break
        time.sleep(1)
    else:
        raise RuntimeError("Garden health check failed")
except BaseException:
    point(old)
    restart()
    raise
'''.replace("RELEASE", repr(release))
    ssh("python3 -c " + shlex.quote(activate))


if __name__ == "__main__":
    main()
