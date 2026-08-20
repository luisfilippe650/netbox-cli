from typing import Annotated

import typer

from netbox_cli.cli.common import execute, make_service
from netbox_cli.presentation.output import OutputFormat
from netbox_cli.schemas.devices import AddManufacturer
from netbox_cli.service.devices import ManufacturersService

app = typer.Typer(help="Gerencia fabricantes.", no_args_is_help=True)


@app.command("post")
def post_manufacturer(
    name: Annotated[str, typer.Option("--name", "-n")],
    comments: Annotated[
        str | None, typer.Option("--comments", "--comment", help="Comentário opcional.")
    ] = None,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Adiciona um fabricante."""
    execute(
        lambda: make_service(ManufacturersService).create(
            AddManufacturer(name=name, comments=comments)
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
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Exclui um fabricante pelo ID."""

    def operation() -> dict[str, object]:
        make_service(ManufacturersService).delete(manufacturer_id)
        return {"deleted": True, "resource": "manufacturer", "id": manufacturer_id}

    execute(operation, output=output, title="Fabricante removido")
