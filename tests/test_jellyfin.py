import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


class JellyfinConfigTest(unittest.TestCase):
    def test_direct_https_preserves_private_origin_fallback(self):
        service = yaml.safe_load((ROOT / "hosts/newport/compose.yml").read_text())["services"]["jellyfin"]
        labels = dict(label.split("=", 1) for label in service["labels"])
        self.assertEqual(labels["traefik.http.routers.jellyfin.entrypoints"], "websecure")
        self.assertEqual(labels["traefik.http.routers.jellyfin.tls.certresolver"], "newporthttp")
        self.assertEqual(labels["traefik.http.routers.jellyfin-origin.service"], "jellyfin")
        self.assertIn("ClientIP(`100.124.6.111/32`)", labels["traefik.http.routers.jellyfin-origin.rule"])
        zone = yaml.safe_load((ROOT / "dns/zones/rotund.org.yaml").read_text())
        self.assertEqual(zone["jellyfin"]["value"], "home.jackharrhy.dev.")
        config = yaml.safe_load((ROOT / "dns/config.yaml").read_text())
        self.assertEqual(config["zones"]["jackharrhy.dev."]["sources"], ["config", "home"])
        self.assertEqual(config["providers"]["home"]["class"], "octodns_ddns.DdnsSource")
        home_zone = yaml.safe_load((ROOT / "dns/zones/jackharrhy.dev.yaml").read_text())
        self.assertNotIn("home", home_zone)
        self.assertEqual(home_zone["craft"]["type"], "CNAME")
        self.assertEqual(home_zone["craft"]["value"], "home.jackharrhy.dev.")

    def test_only_curated_media_is_exposed_read_only(self):
        service = yaml.safe_load((ROOT / "hosts/newport/compose.yml").read_text())["services"]["jellyfin"]
        mounts = [v for v in service["volumes"] if isinstance(v, dict) and (v["source"].startswith("/mnt/stash/media") or v["target"].startswith("/data"))]
        self.assertEqual(len(mounts), 3)
        expected = {f"/mnt/stash/media/library/{kind}": f"/data/library/{kind}" for kind in ("movies", "tv", "documentaries")}
        self.assertEqual({m["source"]: m["target"] for m in mounts}, expected)
        self.assertTrue(all(m["read_only"] and not m["bind"]["create_host_path"] for m in mounts))
        self.assertFalse(any("/mnt/stash/media" in v for v in service["volumes"] if isinstance(v, str)))
        self.assertEqual(service["user"], "1000:1000")
        self.assertIn("65536", service["group_add"])
        self.assertEqual(service["ports"], ["127.0.0.1:8096:8096"])

    def test_native_auth_and_backup_guarded_updates(self):
        service = yaml.safe_load((ROOT / "hosts/newport/compose.yml").read_text())["services"]["jellyfin"]
        labels = dict(label.split("=", 1) for label in service["labels"])
        self.assertEqual(labels["com.centurylinklabs.watchtower.enable"], "true")
        self.assertEqual(labels["com.centurylinklabs.watchtower.lifecycle.pre-update"], "/bin/sh /infra/backup.sh force")
        routes = yaml.safe_load((ROOT / "hosts/mug/traefik/dynamic/routes.yml").read_text())
        router = routes["http"]["routers"]["jellyfin"]
        self.assertEqual(router["rule"], "Host(`jellyfin.rotund.org`)")
        self.assertEqual(router["service"], "newport-origin")
        self.assertFalse(router.get("middlewares"))
