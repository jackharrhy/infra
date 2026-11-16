"""Read bounded native Auth audit events; never print raw event payloads."""
import argparse
import base64
from datetime import datetime, timezone
import json
from pathlib import Path
import time
import urllib.parse
import urllib.request

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

BASE = "https://auth.jackharrhy.dev"
PRIVATE = Path(__file__).parent / ".runtime-secrets"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--since", required=True)
    parser.add_argument("--until", required=True)
    args = parser.parse_args()
    start, end = (datetime.fromisoformat(v.replace("Z", "+00:00")) for v in (args.since, args.until))
    if start.tzinfo is None or end.tzinfo is None or not 0 < (end - start).total_seconds() <= 600:
        parser.error("Use an explicit-offset window of at most ten minutes")
    credential = json.loads((PRIVATE / "audit-key.json").read_text())
    now = int(time.time())

    def encoded(value):
        return base64.urlsafe_b64encode(json.dumps(value, separators=(",", ":")).encode()).decode().rstrip("=")

    unsigned = encoded({"alg": "RS256", "typ": "JWT", "kid": credential["keyId"]}) + "." + encoded({"iss": credential["userId"], "sub": credential["userId"], "aud": BASE, "iat": now, "exp": now + 60})
    key = serialization.load_pem_private_key(credential["key"].encode(), password=None)
    assertion = unsigned + "." + base64.urlsafe_b64encode(key.sign(unsigned.encode(), padding.PKCS1v15(), hashes.SHA256())).decode().rstrip("=")
    opener = urllib.request.build_opener(NoRedirect)
    request = urllib.request.Request(BASE + "/oauth/v2/token", data=urllib.parse.urlencode({"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": assertion, "scope": "openid urn:zitadel:iam:org:project:id:zitadel:aud"}).encode())
    with opener.open(request, timeout=30) as response:
        token = json.load(response)["access_token"]
    request = urllib.request.Request(BASE + "/admin/v1/events/_search", data=json.dumps({"eventTypes": ["auth_request.added"], "range": {"since": args.since, "until": args.until}, "limit": 20}).encode(), headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
    with opener.open(request, timeout=30) as response:
        result = json.load(response)
    registry = json.loads((Path("/mnt/terrabud/docker-data/newport/jack-auth/ui/.ref-preview-applications.runtime.json")).read_text())
    events = result.get("events", [])
    print(json.dumps({"status": "audit-read-ok", "count": len(events), "limit": 20}))
    for event in events:
        payload = event.get("payload", {})
        if not isinstance(payload, dict):
            print(json.dumps({"status": "unsupported-payload-shape"}))
            continue
        scopes = payload.get("scope", [])
        if not isinstance(scopes, list):
            continue
        targets = [a for a in registry if f"urn:zitadel:iam:org:project:id:{a['projectId']}:aud" in scopes]
        app = targets[0] if len(targets) == 1 else None
        permissions = [p for p in (app or {}).get("delegatedPermissions", []) if f"urn:zitadel:iam:org:project:role:{p}" in scopes]
        callback = urllib.parse.urlsplit(payload.get("redirect_uri", ""))
        standard = {"openid", "profile", "email", "offline_access", "urn:zitadel:iam:org:projects:roles"}
        if app:
            standard.add(f"urn:zitadel:iam:org:project:id:{app['projectId']}:aud")
            standard.update(f"urn:zitadel:iam:org:project:role:{r}" for r in [*app.get("delegatedRoles", []), *app.get("delegatedPermissions", [])])
        print(json.dumps({"timestamp": event.get("creationDate"), "target": "Ref" if app and app["id"] == "ref" else "other-or-unknown", "targetCount": len(targets), "recognizedPermissionCount": len(permissions), "boardsRead": "boards-read" in permissions, "boardsWrite": "boards-write" in permissions, "offlineAccess": "offline_access" in scopes, "executorCallback": callback.scheme == "https" and callback.netloc == "executor.jackharrhy.dev" and callback.path == "/api/oauth/callback", "knownBrowserClient": bool(app and payload.get("client_id") in app.get("clientIds", [])), "adminScope": "urn:zitadel:iam:org:project:role:admin" in scopes, "memberScope": "urn:zitadel:iam:org:project:role:member" in scopes, "openid": "openid" in scopes, "profile": "profile" in scopes, "projectRoles": "urn:zitadel:iam:org:projects:roles" in scopes, "unknownScopeCount": len(set(scopes) - standard)}))


if __name__ == "__main__":
    main()
