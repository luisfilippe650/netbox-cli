import json
from unittest.mock import Mock, patch

from typer.testing import CliRunner

from netbox_cli.app import app

runner = CliRunner()


def test_direct_list_returns_machine_readable_json() -> None:
    service = Mock()
    service.list.return_value = {
        "count": 1,
        "results": [{"id": 1, "name": "Sudeste"}],
    }

    with patch(
        "netbox_cli.cli.organization.regions_cli.make_service",
        return_value=service,
    ):
        result = runner.invoke(app, ["regions", "list", "--search", "sud"])

    assert result.exit_code == 0
    assert json.loads(result.stdout)["results"][0]["name"] == "Sudeste"
    service.list.assert_called_once_with(search="sud", limit=None)


def test_direct_delete_returns_a_json_confirmation() -> None:
    service = Mock()

    with patch(
        "netbox_cli.cli.organization.locations_cli.make_service",
        return_value=service,
    ):
        result = runner.invoke(app, ["locations", "delete", "12"])

    assert result.exit_code == 0
    assert json.loads(result.stdout) == {
        "deleted": True,
        "resource": "location",
        "id": 12,
    }
    service.delete.assert_called_once_with(12)


def test_direct_post_builds_site_model() -> None:
    service = Mock()
    service.create.return_value = {"id": 2, "name": "Matriz"}

    with patch(
        "netbox_cli.cli.organization.sites_cli.make_service",
        return_value=service,
    ):
        result = runner.invoke(
            app,
            ["sites", "post", "--name", "Matriz", "--region", "4"],
        )

    assert result.exit_code == 0
    assert json.loads(result.stdout)["id"] == 2
    model = service.create.call_args.args[0]
    assert model.name == "Matriz"
    assert model.region == 4


def test_no_subcommand_opens_interactive_terminal() -> None:
    client = Mock()

    with patch("netbox_cli.cli.terminal.make_client", return_value=client):
        result = runner.invoke(app, [], input="quit\n")

    assert result.exit_code == 0
    assert "NetBox CLI" in result.stdout
    client.close.assert_called_once_with()
