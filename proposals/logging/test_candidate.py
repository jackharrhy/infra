import json
from pathlib import Path
import unittest
import subprocess
import sys
import tempfile
import yaml
from generate import build

CID = 'a' * 64

class CandidateTests(unittest.TestCase):
    def setUp(self):
        self.v, self.c, self.caps = build({'host': 'newport', 'services': {'example': CID}})

    def test_buffer_transport(self):
        s = self.v['sinks']['central']
        self.assertEqual(s['buffer'], {'type': 'disk', 'max_size': 268435488, 'when_full': 'block'})
        self.assertEqual(s['compression'], 'gzip')
        self.assertEqual(s['framing']['method'], 'newline_delimited')
        self.assertTrue(s['tls']['verify_hostname'])
        self.assertEqual(s['inputs'], ['safe_example'])
        self.assertIn('--dangerously-allow-env-var-interpolation', self.c['services']['vector']['command'])

    def test_mount_and_scope(self):
        mounts = self.c['services']['vector']['volumes']
        bind = mounts[2]
        self.assertEqual(bind['source'], '/var/lib/docker/containers/' + CID)
        self.assertTrue(bind['read_only'])
        self.assertFalse(bind['bind']['create_host_path'])
        self.assertNotIn('socket', json.dumps(self.c))
        self.assertEqual(self.caps['services'], {})
        self.assertEqual(self.v['sources']['example']['include'], [f'/input/example/{CID}-json.log*'])

    def test_invalid_inventories(self):
        for services in ({}, {'bad/service': CID}, {'example': '*'}, {'a': CID, 'b': CID}):
            with self.assertRaises(ValueError):
                build({'host': 'newport', 'services': services})

    def test_hyphenated_service_and_explicit_cap_subset(self):
        inventory = {'host': 'newport', 'services': {'ref-celld': CID, 'other': 'b' * 64},
                     'cap_services': ['ref-celld']}
        vector, _, caps = build(inventory)
        self.assertEqual(vector['transforms']['safe_ref-celld']['inputs'], ['ref-celld'])
        self.assertEqual(vector['sources']['ref-celld']['include'], [f'/input/ref-celld/{CID}-json.log*'])
        self.assertEqual(set(caps['services']), {'ref-celld'})
        self.assertEqual(caps['services']['ref-celld']['logging']['options'], {'max-size': '10m', 'max-file': '3'})
        for invalid in (['unselected'], 'ref-celld', [None]):
            with self.assertRaises(ValueError):
                build({**inventory, 'cap_services': invalid})

    def test_cli_caps_opt_in_and_stale_output_removal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inventory = root / 'inventory.json'
            output = root / 'rendered'
            data = {'host': 'newport', 'services': {'ref-celld': CID}}
            def render():
                inventory.write_text(json.dumps(data))
                subprocess.run([sys.executable, str(Path(__file__).with_name('generate.py')),
                                str(inventory), str(output)], check=True)
            render()
            cap_path = output / 'logging-caps.override.yaml'
            self.assertFalse(cap_path.exists())
            self.assertTrue((output / 'vector.yaml').exists())
            data['cap_services'] = ['ref-celld']
            render()
            self.assertEqual(set(yaml.safe_load(cap_path.read_text())['services']), {'ref-celld'})
            del data['cap_services']
            render()
            self.assertFalse(cap_path.exists())

    def test_native_vector_fixtures(self):
        # Wiring only; executing `vector test` later tests the actual VRL.
        valid, invalid = self.v['tests']
        self.assertEqual(valid['inputs'][0]['insert_at'], 'safe_example')
        raw = json.loads(valid['inputs'][0]['value'])
        self.assertEqual(raw['stream'], 'stderr')
        self.assertIn('SYNTHETIC', raw['log'])
        output = valid['outputs'][0]
        self.assertEqual(output['extract_from'], 'safe_example')
        self.assertIn('assert_eq!(., {', output['conditions'][0]['source'])
        self.assertEqual(invalid['no_outputs_from'], ['safe_example'])
        self.assertEqual(json.loads(invalid['inputs'][0]['value'])['stream'], 'not-a-docker-stream')

    def test_central_and_yaml_roundtrip(self):
        central = yaml.safe_load(Path(__file__).with_name('central.compose.yaml').read_text())
        s = central['services']['victorialogs']
        self.assertEqual(s['image'], 'victoriametrics/victoria-logs:v1.54.0@sha256:ee4e820cac3721f5f5d91641b950c22439593adc4224f9655e5333d5a84c1dfe')
        self.assertEqual(self.c['services']['vector']['image'], 'timberio/vector:0.62.0-debian@sha256:6266b1d35c844918ff1c48ea2ec4f57c2b0664c46f3e17fc2418d5dda1692068')
        self.assertNotIn('ports', s)
        self.assertIn('-retentionPeriod=7d', s['command'])
        self.assertIn('-retention.maxDiskSpaceUsageBytes=8589934592', s['command'])
        for value in (self.v, self.c, self.caps):
            self.assertEqual(yaml.safe_load(yaml.safe_dump(value)), value)

if __name__ == '__main__':
    unittest.main()
