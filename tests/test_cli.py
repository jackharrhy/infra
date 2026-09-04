import unittest
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

import cli


class IsLocalSshTargetTests(unittest.TestCase):
    @patch("cli.socket.getfqdn", return_value="newport.hedgehog-python.ts.net")
    @patch("cli.socket.gethostname", return_value="newport")
    def test_recognizes_local_hostname_and_fqdn(self, _gethostname, _getfqdn):
        self.assertTrue(cli.is_local_ssh_target("jack@newport"))
        self.assertTrue(
            cli.is_local_ssh_target("jack@newport.hedgehog-python.ts.net")
        )

    @patch("cli.socket.getfqdn", return_value="newport.hedgehog-python.ts.net")
    @patch("cli.socket.gethostname", return_value="newport")
    def test_rejects_a_different_host(self, _gethostname, _getfqdn):
        self.assertFalse(cli.is_local_ssh_target("jack@mug"))

    @patch("cli.subprocess.run")
    @patch("cli.is_local_ssh_target", return_value=True)
    def test_runs_local_commands_without_ssh(self, _is_local, run):
        run.return_value.returncode = 0

        result = cli.run_host_command(
            "jack@newport",
            "cd ~/infra && git pull",
            [["git", "pull"]],
            cwd=Path("/home/jack/infra"),
            stream=True,
        )

        self.assertEqual(0, result)
        run.assert_called_once_with(["git", "pull"], cwd=Path("/home/jack/infra"))

    @patch("cli.run_host_command", return_value=0)
    @patch("cli.ssh_run", return_value=0)
    @patch("cli.get_deploy_hosts")
    @patch("cli.load_infra_config", return_value={})
    def test_update_dispatches_a_local_target_without_ssh(
        self, _load_config, get_hosts, _ssh_run, run_host
    ):
        host = {
            "ssh": "jack@newport",
            "repo_path": "~/infra",
            "compose_path": "~/infra/hosts/newport",
        }
        get_hosts.return_value = {"newport": host}

        result = CliRunner().invoke(cli.cli, ["update", "newport"])

        self.assertEqual(0, result.exit_code, result.output)
        run_host.assert_called_once_with(
            "jack@newport",
            "cd ~/infra && git pull",
            [["git", "pull"]],
            cwd=Path("~/infra").expanduser(),
            stream=True,
        )

    @patch("cli.run_host_command", return_value=0)
    @patch("cli.get_deploy_hosts")
    @patch("cli.load_infra_config", return_value={})
    def test_refresh_prunes_all_unused_images(
        self, _load_config, get_hosts, run_host
    ):
        host = {
            "ssh": "jack@newport",
            "repo_path": "~/infra",
            "compose_path": "~/infra/hosts/newport",
        }
        get_hosts.return_value = {"newport": host}

        result = CliRunner().invoke(cli.cli, ["refresh", "newport"])

        self.assertEqual(0, result.exit_code, result.output)
        run_host.assert_called_once_with(
            "jack@newport",
            "cd ~/infra/hosts/newport"
            " && docker compose pull"
            " && docker compose up -d"
            " && docker image prune -a -f",
            [
                ["docker", "compose", "pull"],
                ["docker", "compose", "up", "-d"],
                ["docker", "image", "prune", "-a", "-f"],
            ],
            cwd=Path("~/infra/hosts/newport").expanduser(),
            stream=True,
        )


if __name__ == "__main__":
    unittest.main()
