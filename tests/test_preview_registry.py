import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import yaml
from click.testing import CliRunner

import cli
import preview_registry as p


class PreviewRegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.dynamic = self.root / 'dynamic'
        self.dynamic.mkdir()
        self.compose = self.root / 'compose.yml'
        self.compose.write_text('services: {}\n')
        self.now = 1000000
        self.registry = p.Registry(self.root / 'state', self.dynamic, self.compose,
                                   clock=lambda: self.now, listener=lambda port: None)

    def register(self, name='demo', **kwargs):
        args = dict(name=name, owner='source-owner', purpose='UI review', port=21001)
        args.update(kwargs)
        return self.registry.apply('register', **args)

    def projection(self):
        return (self.dynamic / p.PROJECTION).read_bytes()

    def test_generated_contract_and_private_modes(self):
        self.register(paths=['/', '/login'], prefixes=['/assets/'])
        config = yaml.safe_load(self.projection())['http']
        router = config['routers']['temp-preview-demo']
        self.assertEqual(router, {
            'rule': 'Host(`demo.pi.jackharrhy.dev`) && (Path(`/`) || Path(`/login`) || PathPrefix(`/assets/`))',
            'entryPoints': ['pitailnet'], 'service': 'temp-preview-demo', 'tls': {}})
        self.assertEqual(config['services']['temp-preview-demo'], {
            'loadBalancer': {'passHostHeader': True, 'servers': [{'url': 'http://127.0.0.1:21001'}]}})
        self.assertEqual((self.root / 'state').stat().st_mode & 0o777, 0o700)
        self.assertEqual((self.root / 'state/registry.json').stat().st_mode & 0o777, 0o600)
        self.assertEqual((self.dynamic / p.PROJECTION).stat().st_mode & 0o777, 0o600)

    def test_invalid_names_paths_ports_and_lease_keep_last_good(self):
        self.register()
        old = self.projection()
        for args in [dict(name='*.evil'), dict(name='a.b'), dict(name='Upper'),
                     dict(name='pi'), dict(name='4orm'), dict(name='wonder'), dict(name='browse'),
                     dict(port=8788), dict(port=19988), dict(port=19989), dict(port=80), dict(port=65536),
                     dict(paths=['/`) || Host(`evil']), dict(paths=['/../secret']),
                     dict(prefixes=['/assets']), dict(ttl=0), dict(ttl=p.MAX_TTL + 1),
                     dict(owner='bad\nowner'), dict(purpose='')]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                self.register(**args)
            self.assertEqual(old, self.projection())
        for value in ['0h', '8d', '1s', '24', '-2h']:
            with self.assertRaises(ValueError):
                p.ttl_seconds(value)
        self.assertEqual(p.ttl_seconds('24h'), p.DEFAULT_TTL)

    def test_owner_and_port_collision_no_takeover(self):
        self.register()
        for args in [dict(owner='other'), dict(name='another')]:
            with self.assertRaises(ValueError):
                self.register(**args)
        with self.assertRaises(ValueError):
            self.registry.apply('remove', name='demo', owner='other')
        self.registry.apply('renew', name='demo', owner='source-owner', ttl=120)
        self.assertEqual(self.registry.read()['demo']['expires_at'], self.now + 120)

    def test_permanent_static_and_compose_ports_protected(self):
        self.compose.write_text('services:\n  permanent:\n    ports: ["127.0.0.1:21001:80"]\n')
        with self.assertRaises(ValueError):
            self.register()
        self.compose.write_text('services: {}\n')
        static = {'http': {'routers': {'permanent': {
            'rule': 'Host(`permanent.pi.jackharrhy.dev`)', 'service': 'permanent'}},
            'services': {'permanent': p.service({'port': 21001})}}}
        (self.dynamic / 'routes.yml').write_text(yaml.safe_dump(static))
        with self.assertRaises(ValueError):
            self.register()

    def test_exact_equivalent_adoption_then_static_removal(self):
        entry = {'port': 21001, 'paths': ['/'], 'prefixes': []}
        router = p.route('demo', entry)
        router['service'] = 'old'
        static = {'http': {'routers': {'old': router}, 'services': {'old': p.service(entry)}}}
        path = self.dynamic / 'routes.yml'
        path.write_text(yaml.safe_dump(static))
        with self.assertRaises(ValueError):
            self.register(paths=['/'])
        with self.assertRaises(ValueError):
            self.register(paths=['/login'], adopt=True)
        self.register(paths=['/'], adopt=True)
        path.unlink()
        self.registry.apply('reconcile')
        self.assertIn('temp-preview-demo', yaml.safe_load(self.projection())['http']['routers'])

    def test_expiry_and_remove_are_route_only(self):
        self.register(ttl=60)
        self.now += 61
        leases, expired = self.registry.apply('reconcile')
        self.assertEqual((leases, expired), ({}, ['demo']))
        self.assertEqual(yaml.safe_load(self.projection()), {'http': {'routers': {}, 'services': {}}})
        self.register()
        self.registry.apply('remove', name='demo', owner='source-owner')
        self.assertEqual(self.registry.read(), {})

    def test_failed_projection_write_rolls_back_registry(self):
        self.register()
        old = self.projection()
        state = (self.root / 'state/registry.json').read_bytes()
        original = p.atomic_write
        def fail_projection(path, data):
            if path.name == p.PROJECTION:
                raise OSError('simulated full disk')
            original(path, data)
        with patch.object(p, 'atomic_write', side_effect=fail_projection), self.assertRaises(OSError):
            self.register('second', port=21002)
        self.assertEqual(old, self.projection())
        self.assertEqual(state, (self.root / 'state/registry.json').read_bytes())

    def test_corrupt_or_injected_registry_preserves_projection(self):
        self.register()
        old = self.projection()
        path = self.root / 'state/registry.json'
        data = json.loads(path.read_text())
        data['leases']['demo']['middleware'] = 'evil'
        path.write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            self.registry.apply('reconcile')
        self.assertEqual(old, self.projection())

    def test_concurrent_writers_do_not_lose_leases_or_emit_partial_yaml(self):
        def create(index):
            other = p.Registry(self.root / 'state', self.dynamic, self.compose,
                               clock=lambda: self.now, listener=lambda port: None)
            other.apply('register', name=f'test-{index}', owner=f'owner-{index}',
                        purpose='concurrency', port=22000 + index)
        with ThreadPoolExecutor(max_workers=8) as executor:
            list(executor.map(create, range(16)))
        self.assertEqual(len(self.registry.read()), 16)
        self.assertEqual(len(yaml.safe_load(self.projection())['http']['routers']), 16)
        self.assertEqual(list(self.dynamic.glob('.preview-*.tmp')), [])

    def test_literal_listener_rejects_other_interfaces(self):
        for address, okay in [('127.0.0.1', True), ('0.0.0.0', False),
                              ('100.123.66.70', False), ('[::]', False)]:
            with patch.object(p.subprocess, 'run') as run:
                run.return_value.stdout = f'LISTEN 0 511 {address}:21001 0.0.0.0:*\n'
                if okay:
                    p.loopback_listener(21001)
                else:
                    with self.assertRaises(ValueError):
                        p.loopback_listener(21001)

    def test_cli_register_list_renew_remove(self):
        with patch.object(p.socket, 'gethostname', return_value='newport'), \
             patch.object(p, 'Registry', return_value=self.registry):
            runner = CliRunner()
            base = ['preview']
            result = runner.invoke(cli.cli, base + ['register', 'demo', '--port', '21001',
                                   '--owner', 'source-owner', '--purpose', 'UI review'])
            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn('https://demo.pi.jackharrhy.dev', result.output)
            for args in [['list'], ['renew', 'demo', '--owner', 'source-owner'],
                         ['remove', 'demo', '--owner', 'source-owner'], ['reconcile']]:
                result = runner.invoke(cli.cli, base + args)
                self.assertEqual(result.exit_code, 0, result.output)
