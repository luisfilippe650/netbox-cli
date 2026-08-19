from typing import Annotated

import typer

from netbox_cli.cli.common import execute, make_service
from netbox_cli.presentation.output import OutputFormat
from netbox_cli.schemas.organization.locations_dto import AddLocation
from netbox_cli.service.organization.locations_service import LocationsService

app = typer.Typer(help="Gerencia locais do NetBox.", no_args_is_help=True)


def post_location(
    name: Annotated[str, typer.Option("--name", "-n")],
    site: Annotated[int, typer.Option("--site", help="ID do site.", min=1)],
    slug: Annotated[str | None, typer.Option()] = None,
    status: Annotated[str, typer.Option()] = "active",
    parent: Annotated[
        int | None, typer.Option("--parent", help="ID do local pai.", min=1)
    ] = None,
    description: Annotated[str, typer.Option("--description", "-d")] = "",
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Cria um local associado a um site."""
    execute(
        lambda: make_service(LocationsService).create(
            AddLocation(
                name=name,
                site=site,
                slug=slug,
                status=status,
                parent=parent,
                description=description,
            )
        ),
        output=output,
        title="Local criado",
    )


app.command("post")(post_location)
app.command("create", hidden=True)(post_location)


@app.command("view")
def view_location(
    location_id: Annotated[int, typer.Argument(min=1)],
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Exibe um local pelo ID."""
    execute(
        lambda: make_service(LocationsService).get(location_id),
        output=output,
        title="Local",
    )


@app.command("list")
def list_locations(
    search: Annotated[str | None, typer.Option("--search", "-s")] = None,
    limit: Annotated[int | None, typer.Option(min=0)] = None,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Lista locais, opcionalmente filtrados."""
    execute(
        lambda: make_service(LocationsService).list(search=search, limit=limit),
        output=output,
        title="Locais",
    )


@app.command("delete")
def delete_location(
    location_id: Annotated[int, typer.Argument(min=1)],
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Exclui um local pelo ID."""

    def operation() -> dict[str, object]:
        make_service(LocationsService).delete(location_id)
        return {"deleted": True, "resource": "location", "id": location_id}

    execute(operation, output=output, title="Local removido")
