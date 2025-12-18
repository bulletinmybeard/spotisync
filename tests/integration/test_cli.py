from click.testing import CliRunner

from src.cli.cli import cli


class TestCLI:
    def test_cli_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "spotisync" in result.output.lower()
        assert "sync" in result.output
        assert "config" in result.output
        assert "auth" in result.output

    def test_cli_no_command_shows_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli)

        assert result.exit_code == 0
        assert "spotisync" in result.output.lower()

    def test_config_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["config", "--help"])

        assert result.exit_code == 0
        assert "config" in result.output.lower()

    def test_auth_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["auth", "--help"])

        assert result.exit_code == 0

    def test_sync_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["sync", "--help"])

        assert result.exit_code == 0
        assert "dry-run" in result.output.lower() or "sync" in result.output.lower()

    def test_status_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["status", "--help"])

        assert result.exit_code == 0

    def test_init_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["init", "--help"])

        assert result.exit_code == 0
