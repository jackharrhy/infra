import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


class CanonicalHarrhyImagesTest(unittest.TestCase):
    def test_production_tracks_canonical_publishers(self):
        expected = {
            "newport": {
                "8ballworld": "pool",
                "artbin": "artbin",
                "burger": "burger",
                "maps-collaboration": "worldview-collaboration",
                "maps-compiler": "worldview-compiler",
                "maps-gower-compiler": "worldview-compiler",
                "maps-service": "worldview-service",
                "maps-ui": "worldview",
                "marky": "marky",
                "ref-celld": "ref",
                "steve": "letters-to-steve",
                "rotund_org": "rotund",
            },
            "mug": {
                "8mb": "8mb",
                "gurgur": "gurgur",
                "jackharrhy": "garden",
                "lists": "lists",
                "radio-celld": "radio",
                "teacms": "teacms",
            },
        }
        for host, entries in expected.items():
            services = yaml.safe_load((ROOT / "hosts" / host / "compose.yml").read_text())["services"]
            for service, image in entries.items():
                with self.subTest(host=host, service=service):
                    self.assertEqual(services[service]["image"], f"ghcr.io/jackharrhy/{image}:latest")

    def test_retired_cmd_cannot_be_resurrected_by_refresh(self):
        config = yaml.safe_load((ROOT / "hosts/newport/compose.yml").read_text())
        for service in ("cmd", "cmd_postgres", "cmd_garage"):
            self.assertNotIn(service, config["services"])
        self.assertNotIn("cmd_db", config["networks"])
        routes = yaml.safe_load((ROOT / "hosts/mug/traefik/dynamic/routes.yml").read_text())
        self.assertNotIn("cmd", routes["http"]["routers"])
