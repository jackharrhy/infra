import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def labels(service):
    return dict(item.split("=", 1) for item in service["labels"])


class CleanuparrConfigTest(unittest.TestCase):
    def test_ui_and_api_have_no_public_gate_bypass(self):
        services = yaml.safe_load((ROOT / "hosts/newport/compose.yml").read_text())["services"]
        app = services["cleanuparr"]
        self.assertEqual(labels(app).get("traefik.enable"), "true")
        self.assertEqual(labels(app).get("traefik.http.routers.cleanuparr.middlewares"), "cleanuparr-auth")
        self.assertEqual(app["ports"], ["127.0.0.1:11011:11011"])
        self.assertNotIn("Path", labels(app)["traefik.http.routers.cleanuparr.rule"])
        auth = services["cleanuparr-auth"]
        self.assertEqual(auth["env_file"], [".runtime-secrets/cleanuparr-auth.env"])
        self.assertEqual(auth["environment"]["OAUTH2_PROXY_COOKIE_NAME"], "__Host-cleanuparr_auth")
        self.assertIn("lifecycle.pre-update", " ".join(app["labels"]))
