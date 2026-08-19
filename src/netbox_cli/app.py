import typer

from netbox_cli.cli.organization.locations_cli import app as locations_app
from netbox_cli.cli.organization.regions_cli import app as regions_app
from netbox_cli.cli.organization.sites_cli import app as sites_app
from netbox_cli.cli.terminal import run_terminal

app = typer.Typer(
    help="CLI interativa e direta para o NetBox.",
    invoke_without_command=True,
)
app.add_typer(regions_app, name="regions")
app.add_typer(sites_app, name="sites")
app.add_typer(locations_app, name="locations")


@app.callback()
def main(ctx: typer.Context) -> None:
    """Sem subcomando, abre o terminal interativo com Rich."""
    if ctx.invoked_subcommand is None:
        run_terminal()
