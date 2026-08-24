from pathlib import Path
from typing import Annotated, Literal

import typer

from netbox_cli import __version__
from netbox_cli.cli.automation_cli import (
    inspect_device,
    inventory,
    search,
    status,
    trace,
    tree,
)
from netbox_cli.cli.devices.device_roles_cli import app as device_roles_app
from netbox_cli.cli.devices.connectivity_cli import (
    cables_app,
    console_ports_app,
    front_ports_app,
    interfaces_app,
    power_ports_app,
    rear_ports_app,
)
from netbox_cli.cli.devices.device_types_cli import app as device_types_app
from netbox_cli.cli.devices.devices_cli import app as devices_app
from netbox_cli.cli.devices.manufacturers_cli import app as manufacturers_app
from netbox_cli.cli.import_cli import import_resources
from netbox_cli.cli.login import login
from netbox_cli.cli.organization.locations_cli import app as locations_app
from netbox_cli.cli.organization.regions_cli import app as regions_app
from netbox_cli.cli.organization.sites_cli import app as sites_app
from netbox_cli.cli.racks.rack_groups_cli import app as rack_groups_app
from netbox_cli.cli.racks.racks_cli import app as racks_app
from netbox_cli.cli.terminal import run_terminal
from netbox_cli.runtime import RuntimeOptions, configure

app = typer.Typer(
    help="CLI interativa e direta para o NetBox.",
    invoke_without_command=True,
)
app.add_typer(regions_app, name="regions")
app.add_typer(sites_app, name="sites")
app.add_typer(sites_app, name="site")
app.add_typer(locations_app, name="locations")
app.add_typer(rack_groups_app, name="rack-groups")
app.add_typer(racks_app, name="racks")
app.add_typer(racks_app, name="rack")
app.add_typer(manufacturers_app, name="manufacturers")
app.add_typer(interfaces_app, name="interfaces")
app.add_typer(front_ports_app, name="front-ports")
app.add_typer(rear_ports_app, name="rear-ports")
app.add_typer(console_ports_app, name="console-ports")
app.add_typer(power_ports_app, name="power-ports")
app.add_typer(cables_app, name="cables")
app.add_typer(device_roles_app, name="device-roles")
app.add_typer(device_types_app, name="device-types")
app.add_typer(devices_app, name="devices")
app.add_typer(devices_app, name="device")
app.command("inspect")(inspect_device)
app.command("search")(search)
app.command("inventory")(inventory)
app.command("trace")(trace)
app.command("status")(status)
app.command("tree")(tree)
app.command("login")(login)
app.command("import")(import_resources)


def version_callback(show_version: bool) -> None:
    """Exibe a versão sem carregar configuração ou abrir o terminal."""
    if show_version:
        typer.echo(f"netbox-cli {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    ctx: typer.Context,
    version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            callback=version_callback,
            is_eager=True,
            help="Exibe a versão da CLI e encerra.",
        ),
    ] = None,
    url: Annotated[
        str | None,
        typer.Option("--url", help="URL do NetBox; sobrescreve ambiente e arquivo."),
    ] = None,
    token: Annotated[
        str | None,
        typer.Option(
            "--token", help="Token da API; prefira NETBOX_TOKEN em automações."
        ),
    ] = None,
    timeout: Annotated[
        float | None,
        typer.Option("--timeout", min=0.001, help="Timeout HTTP em segundos."),
    ] = None,
    config: Annotated[
        Path | None,
        typer.Option("--config", help="Arquivo YAML de configuração."),
    ] = None,
    output: Annotated[
        Literal["json", "human", "id"] | None,
        typer.Option(
            "--output",
            help="Formato global: json, human ou somente id.",
        ),
    ] = None,
    retries: Annotated[
        int,
        typer.Option(
            "--retries",
            min=0,
            help="Novas tentativas para leituras com falha transitória.",
        ),
    ] = 2,
    backoff: Annotated[
        float,
        typer.Option(
            "--backoff",
            min=0,
            help="Espera inicial entre tentativas; dobra a cada falha.",
        ),
    ] = 0.5,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Mostra requisições e tentativas."),
    ] = False,
    debug: Annotated[
        bool,
        typer.Option("--debug", help="Inclui detalhes técnicos e traceback."),
    ] = False,
) -> None:
    """Sem subcomando, abre o terminal interativo com Rich."""
    configure(
        RuntimeOptions(
            url=url,
            token=token,
            timeout=timeout,
            config_path=config,
            output=output,
            retries=retries,
            backoff=backoff,
            verbose=verbose,
            debug=debug,
        )
    )

    if ctx.invoked_subcommand is None:
        run_terminal()
