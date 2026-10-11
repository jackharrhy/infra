import json
import unittest
from unittest.mock import patch

from click.testing import CliRunner

import cli


class NasSearchTests(unittest.TestCase):
    @patch("cli._synology_client")
    def test_search_uses_existing_auth_and_returns_json(self, factory):
        response = {"success": True, "data": {"total": 1, "hits": [
            {"SYNOMDSharePath": "/newport/backup.zip", "SYNOMDFSSize": "123"}
        ]}}
        factory.return_value.search.return_value = response
        result = CliRunner().invoke(cli.cli, ["nas", "search", "backup", "--json"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(json.loads(result.stdout), response)
        factory.assert_called_once_with("universal_search")
        factory.return_value.search.assert_called_once_with("backup")
        factory.return_value.logout.assert_called_once()


    @patch("cli._synology_client")
    def test_filename_search_paginates_on_server(self, factory):
        factory.return_value.gen_list = {"SYNO.Finder.FileIndexing.Search": {"path": "entry.cgi"}}
        factory.return_value.request_data.return_value = {
            "success": True, "data": {"total": 12, "hits": [
                {"SYNOMDSharePath": "/archive/whitelist.json", "SYNOMDFSSize": "42"}
            ]}}
        result = CliRunner().invoke(cli.cli, ["nas", "search", "whitelist", "--name-only", "--limit", "5", "--offset", "10"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("Showing 1 of 12", result.output)
        self.assertIn("/archive/whitelist.json", result.output)
        params = factory.return_value.request_data.call_args.args[2]
        self.assertEqual(params["from"], 10)
        self.assertEqual(params["size"], 5)
        self.assertEqual([r["field"] for r in json.loads(params["search_weight_list"])], ["SYNOMDSearchFileName"])
        factory.return_value.search.assert_not_called()

    @patch("cli._synology_client")
    def test_partial_or_malformed_results_fail_closed(self, factory):
        for response in ["error", {"success": False}, {"success": True, "data": {"has_error": True, "hits": [], "total": 0}}, {"success": True, "data": {"hits": "invalid", "total": 2}}]:
            with self.subTest(response=response):
                factory.return_value.search.return_value = response
                result = CliRunner().invoke(cli.cli, ["nas", "search", "test"])
                self.assertEqual(result.exit_code, 1, result.output)
                self.assertIn("Error:", result.output)

    @patch("cli._synology_client")
    def test_request_exception_does_not_leak_session(self, factory):
        factory.return_value.search.side_effect = RuntimeError("https://nas/?_sid=private-session")
        result = CliRunner().invoke(cli.cli, ["nas", "search", "test"])
        self.assertEqual(result.exit_code, 1)
        self.assertNotIn("private-session", result.output)
        factory.return_value.logout.assert_called_once()

    @patch("cli._synology_client")
    def test_invalid_pagination_does_not_authenticate(self, factory):
        for options in [["--limit", "0"], ["--limit", "1001"], ["--offset", "-1"]]:
            result = CliRunner().invoke(cli.cli, ["nas", "search", "test", *options])
            self.assertEqual(result.exit_code, 2)
        factory.assert_not_called()


if __name__ == "__main__":
    unittest.main()
