from typer.testing import CliRunner

from netbox_cli.app import app


runner = CliRunner()

CRUD_COMMANDS = {"create", "get", "list", "update", "delete"}
CRUD_GROUPS = (
    "regions",
    "sites",
    "locations",
    "rack-groups",
    "racks",
    "manufacturers",
    "device-types",
    "device-roles",
    "devices",
    "interfaces",
    "front-ports",
    "rear-ports",
    "console-ports",
    "power-ports",
    "cables",
)


def test_crud_groups_expose_the_standard_commands() -> None:
    for group in CRUD_GROUPS:
        result = runner.invoke(app, [group, "--help"])

        assert result.exit_code == 0, result.output
        for command in CRUD_COMMANDS:
            assert command in result.output, f"{group} não exibe {command}"


def test_legacy_command_aliases_remain_available() -> None:
    aliases = {
        "regions": ("post", "view"),
        "sites": ("post", "view"),
        "locations": ("post", "view"),
        "rack-groups": ("post", "all"),
        "racks": ("post", "all"),
        "manufacturers": ("post", "all"),
        "device-types": ("post", "all"),
        "device-roles": ("post", "all"),
        "devices": ("post", "all"),
    }

    for group, commands in aliases.items():
        for command in commands:
            result = runner.invoke(app, [group, command, "--help"])

            assert result.exit_code == 0, f"{group} {command}: {result.output}"
