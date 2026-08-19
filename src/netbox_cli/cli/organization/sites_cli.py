from typing import Annotated

import typer

from netbox_cli.cli.common import execute, execute_operation, make_service
from netbox_cli.presentation.details import DetailOutputFormat, render_site_status
from netbox_cli.presentation.output import OutputFormat
from netbox_cli.schemas.organization.sites_dto import AddSite
from netbox_cli.service.organization.sites_service import SitesService

app = typer.Typer(help="Gerencia sites do NetBox.", no_args_is_help=True)


def post_site(
    name: Annotated[str, typer.Option("--name", "-n")],
    slug: Annotated[str | None, typer.Option()] = None,
    status: Annotated[str, typer.Option()] = "active",
    region: Annotated[
        int | None, typer.Option("--region", help="ID da região.", min=1)
    ] = None,
    description: Annotated[str, typer.Option("--description", "-d")] = "",
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Cria um site."""
    execute(
        lambda: make_service(SitesService).create(
            AddSite(
                name=name,
                slug=slug,
                status=status,
                region=region,
                description=description,
            )
        ),
        output=output,
        title="Site criado",
    )


app.command("post")(post_site)
app.command("create", hidden=True)(post_site)


@app.command("view")
def view_site(
    site_id: Annotated[int, typer.Argument(min=1)],
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Exibe um site pelo ID."""
    execute(
        lambda: make_service(SitesService).get(site_id), output=output, title="Site"
    )


@app.command("list")
def list_sites(
    search: Annotated[str | None, typer.Option("--search", "-s")] = None,
    limit: Annotated[int | None, typer.Option(min=0)] = None,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Lista sites, opcionalmente filtrados."""
    execute(
        lambda: make_service(SitesService).list(search=search, limit=limit),
        output=output,
        title="Sites",
    )


@app.command("delete")
def delete_site(
    site_id: Annotated[int, typer.Argument(min=1)],
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Exclui um site pelo ID."""

    def operation() -> dict[str, object]:
        make_service(SitesService).delete(site_id)
        return {"deleted": True, "resource": "site", "id": site_id}

    execute(operation, output=output, title="Site removido")


@app.command("status")
def site_status(
    name: Annotated[str, typer.Argument(help="Nome exato do site.")],
    output: Annotated[
        DetailOutputFormat, typer.Option("--output", "-o")
    ] = DetailOutputFormat.human,
) -> None:
    """Resume racks, dispositivos, capacidade e fabricantes de um site."""
    result = execute_operation(lambda: make_service(SitesService).status(name))
    render_site_status(result, output)
