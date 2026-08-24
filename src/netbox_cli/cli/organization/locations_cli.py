from typing import Annotated

import typer

from netbox_cli.cli.common import (
    create_resource,
    delete_resource,
    execute,
    explicit_update_fields,
    make_service,
    update_resource,
)
from netbox_cli.presentation.output import OutputFormat
from netbox_cli.schemas.organization.locations_dto import AddLocation, UpdateLocation
from netbox_cli.service.organization.locations_service import LocationsService

app = typer.Typer(help="Gerencia locais do NetBox.", no_args_is_help=True)


def post_location(
    ctx: typer.Context,
    name: Annotated[str, typer.Option("--name", "-n")],
    site: Annotated[str, typer.Option("--site", help="ID, nome ou slug do site.")],
    slug: Annotated[str | None, typer.Option()] = None,
    status: Annotated[str, typer.Option()] = "active",
    parent: Annotated[
        str | None, typer.Option("--parent", help="ID, nome ou slug do local pai.")
    ] = None,
    description: Annotated[str, typer.Option("--description", "-d")] = "",
    ensure: Annotated[
        bool, typer.Option("--ensure", help="Converge nome dentro do site.")
    ] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Cria um local associado a um site."""
    execute(
        lambda: create_resource(
            LocationsService,
            AddLocation(
                name=name,
                site=site,
                slug=slug,
                status=status,
                parent=parent,
                description=description,
            ),
            ensure=ensure,
            dry_run=dry_run,
            filters={"site_id": site},
            update_fields=explicit_update_fields(
                ctx,
                required={"name", "site"},
                optional={"slug", "status", "parent", "description"},
            ),
        ),
        output=output,
        title="Local criado",
    )


app.command("create")(post_location)
app.command("post", hidden=True)(post_location)


@app.command("get")
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


app.command("view", hidden=True)(view_location)


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


@app.command("update")
def update_location(
    location_id: Annotated[int, typer.Argument(min=1)],
    name: Annotated[str | None, typer.Option("--name", "-n")] = None,
    site: Annotated[
        str | None, typer.Option("--site", help="ID, nome ou slug do site.")
    ] = None,
    slug: Annotated[str | None, typer.Option("--slug")] = None,
    status: Annotated[str | None, typer.Option("--status")] = None,
    parent: Annotated[
        str | None, typer.Option("--parent", help="ID, nome ou slug do local pai.")
    ] = None,
    description: Annotated[str | None, typer.Option("--description", "-d")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Atualiza somente os campos informados de um local."""
    execute(
        lambda: update_resource(
            LocationsService,
            location_id,
            UpdateLocation(
                name=name,
                site=site,
                slug=slug,
                status=status,
                parent=parent,
                description=description,
            ),
            dry_run=dry_run,
        ),
        output=output,
        title="Local atualizado",
    )


@app.command("delete")
def delete_location(
    location_id: Annotated[int, typer.Argument(min=1)],
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    ignore_not_found: Annotated[bool, typer.Option("--ignore-not-found")] = False,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Exclui um local pelo ID."""

    execute(
        lambda: delete_resource(
            LocationsService,
            location_id,
            resource="location",
            dry_run=dry_run,
            ignore_not_found=ignore_not_found,
        ),
        output=output,
        title="Local removido",
    )
