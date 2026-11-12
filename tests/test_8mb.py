import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


class EightMbConfigTest(unittest.TestCase):
    def test_harrhy_host_uses_private_aggregate_storage(self):
        service = yaml.safe_load((ROOT / "hosts/mug/compose.yml").read_text())["services"]["8mb"]
        labels = dict(label.split("=", 1) for label in service["labels"])
        self.assertEqual(labels["traefik.http.services.8mb.loadbalancer.server.port"], "5188")
        self.assertEqual(service["user"], "1000:1000")
        self.assertEqual(service["environment"]["APP_ORIGIN"], "https://jackharrhy.dev")
        self.assertEqual(service["environment"]["DIAGNOSTICS_DB_FILE"], "/app/data/diagnostics.sqlite")
        self.assertEqual(service["command"], ["/bin/sh", "-c", "umask 077; exec node --env-file-if-exists=.env --import remix/node-tsx server.ts"])
        self.assertEqual(service["volumes"], [{"type": "bind", "source": "./volumes/8mb-diagnostics", "target": "/app/data", "bind": {"create_host_path": False}}])
        self.assertTrue(service["read_only"])
        self.assertNotIn("env_file", service)
        self.assertNotIn("ports", service)
        self.assertEqual(labels["traefik.http.routers.8mb.rule"], "Host(`jackharrhy.dev`) && (Path(`/8mb`) || PathPrefix(`/8mb/`))")
