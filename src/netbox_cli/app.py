from pathlib import Path
from typing import Annotated, Literal

import typer

from netbox_cli.cli.automation_cli import (
    inspect_device,
    inventory,
    search,
    status,
    trace,
    tree,
)
from netbox_cli.cli.devices.device_types_cli import app as device_types_app
from netbox_cli.cli.devices.devices_cli import app as devices_app
from netbox_cli.cli.devices.manufacturers_cli import app as manufacturers_app
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


@app.callback()
def main(
    ctx: typer.Context,
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
        Literal["json", "human"] | None,
        typer.Option(
            "--output",
            help="Formato global: json força saída e erros estruturados.",
        ),
    ] = None,
) -> None:
    """Sem subcomando, abre o terminal interativo com Rich."""
    configure(
        RuntimeOptions(
            url=url,
            token=token,
            timeout=timeout,
            config_path=config,
            output=output,
        )
    )
    if ctx.invoked_subcommand is None:
        run_terminal()
