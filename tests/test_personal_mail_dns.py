import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


class PersonalMailDnsTests(unittest.TestCase):
    def setUp(self):
        self.zone = yaml.safe_load((ROOT / 'dns/zones/jackharrhy.com.yaml').read_text())

    def test_account_specific_regional_mx_at_apex_and_wildcard(self):
        # Account-provided US endpoints, not generic in1/in2 documentation values.
        expected = [
            {'exchange': 'us1-smtp.messagingengine.com.', 'preference': 10},
            {'exchange': 'us2-smtp.messagingengine.com.', 'preference': 20},
        ]
        for name in ['', '*']:
            with self.subTest(name=name):
                records = [r for r in self.zone[name] if r['type'] == 'MX']
                self.assertEqual(records, [{'ttl': 300, 'type': 'MX', 'values': expected}])

    def test_one_overlap_spf_and_additive_dkim(self):
        spf = [r for r in self.zone[''] if r['type'] == 'TXT'
               and r.get('value', '').startswith('v=spf1')]
        self.assertEqual(spf, [{'ttl': 300, 'type': 'TXT',
                               'value': 'v=spf1 include:zoho.com include:spf.messagingengine.com ~all'}])
        for i in [1, 2, 3]:
            self.assertEqual(self.zone[f'fm{i}._domainkey'], {
                'ttl': 300, 'type': 'CNAME',
                'value': f'fm{i}.jackharrhy.com.dkim.fmhosted.com.'})

    def test_site_and_nameservers_preserved(self):
        for name in ['', '*']:
            records = {r['type']: r for r in self.zone[name]}
            self.assertEqual(records['A']['value'], '142.93.144.29')
            self.assertEqual(records['AAAA']['value'], '2604:a880:cad:d0::dff:a001')
        self.assertEqual(self.zone['www'], {'ttl': 43200, 'type': 'CNAME', 'value': 'jackharrhy.com.'})
        ns = next(r for r in self.zone[''] if r['type'] == 'NS')
        self.assertEqual(ns['values'], ['ns1.digitalocean.com.', 'ns2.digitalocean.com.', 'ns3.digitalocean.com.'])
        self.assertEqual(ns['ttl'], 1800)
