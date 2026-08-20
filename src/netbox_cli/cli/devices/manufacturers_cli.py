from typing import Annotated

import typer

from netbox_cli.cli.common import (
    create_resource,
    delete_resource,
    execute,
    explicit_update_fields,
    make_service,
)
from netbox_cli.presentation.output import OutputFormat
from netbox_cli.schemas.devices import AddManufacturer
from netbox_cli.service.devices import ManufacturersService

app = typer.Typer(help="Gerencia fabricantes.", no_args_is_help=True)


@app.command("post")
def post_manufacturer(
    ctx: typer.Context,
    name: Annotated[str, typer.Option("--name", "-n")],
    comments: Annotated[
        str | None, typer.Option("--comments", "--comment", help="Comentário opcional.")
    ] = None,
    ensure: Annotated[bool, typer.Option("--ensure", help="Cria ou converge pelo nome.")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Adiciona um fabricante."""
    execute(
        lambda: create_resource(
            ManufacturersService,
            AddManufacturer(name=name, comments=comments),
            ensure=ensure,
            dry_run=dry_run,
            update_fields=explicit_update_fields(
                ctx,
                required={"name"},
                optional={"comments"},
            ),
        ),
        output=output,
        title="Fabricante criado",
    )


@app.command("get")
def get_manufacturer(
    manufacturer_id: Annotated[int, typer.Argument(min=1)],
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Obtém um fabricante pelo ID."""
    execute(
        lambda: make_service(ManufacturersService).get(manufacturer_id),
        output=output,
        title="Fabricante",
    )


@app.command("all")
def all_manufacturers(
    search: Annotated[str | None, typer.Option("--search", "-s")] = None,
    limit: Annotated[int | None, typer.Option(min=0)] = 0,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Lista fabricantes."""
    execute(
        lambda: make_service(ManufacturersService).list(search=search, limit=limit),
        output=output,
        title="Fabricantes",
    )


app.command("list", hidden=True)(all_manufacturers)


@app.command("delete")
def delete_manufacturer(
    manufacturer_id: Annotated[int, typer.Argument(min=1)],
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    ignore_not_found: Annotated[bool, typer.Option("--ignore-not-found")] = False,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Exclui um fabricante pelo ID."""

    execute(
        lambda: delete_resource(
            ManufacturersService,
            manufacturer_id,
            resource="manufacturer",
            dry_run=dry_run,
            ignore_not_found=ignore_not_found,
        ),
        output=output,
        title="Fabricante removido",
    )
