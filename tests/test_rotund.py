import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


class RotundConfigTest(unittest.TestCase):
    def test_harrhy_directory_preserves_its_existing_ingress_and_secret_input(self):
        service = yaml.safe_load((ROOT / "hosts/newport/compose.yml").read_text())["services"]["rotund_org"]
        labels = dict(label.split("=", 1) for label in service["labels"])
        self.assertEqual(service["image"], "ghcr.io/jackharrhy/rotund:latest")
        self.assertEqual(service["env_file"], [".runtime-secrets/rotund-portal.env"])
        self.assertEqual(labels["traefik.http.services.rotund.loadbalancer.server.port"], "80")
        self.assertEqual(labels["traefik.http.routers.rotund.rule"], "Host(`rotund.org`)")
        self.assertEqual(labels["com.centurylinklabs.watchtower.enable"], "true")
        self.assertEqual(service["user"], "1000:1000")
        self.assertTrue(service["read_only"])
        self.assertNotIn("volumes", service)
        self.assertNotIn("ports", service)
