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
from netbox_cli.cli.organization.locations_cli import app as locations_app
from netbox_cli.cli.organization.regions_cli import app as regions_app
from netbox_cli.cli.organization.sites_cli import app as sites_app
from netbox_cli.cli.racks.rack_groups_cli import app as rack_groups_app
from netbox_cli.cli.racks.racks_cli import app as racks_app
from netbox_cli.cli.terminal import run_terminal

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


@app.callback()
def main(ctx: typer.Context) -> None:
    """Sem subcomando, abre o terminal interativo com Rich."""
    if ctx.invoked_subcommand is None:
        run_terminal()
