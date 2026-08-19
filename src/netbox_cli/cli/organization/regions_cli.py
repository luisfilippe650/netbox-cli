from typing import Annotated

import typer

from netbox_cli.cli.common import execute, make_service
from netbox_cli.presentation.output import OutputFormat
from netbox_cli.schemas.organization.regions_dto import AddRegion
from netbox_cli.service.organization.regions_service import RegionsService

app = typer.Typer(help="Gerencia regiões do NetBox.", no_args_is_help=True)


def post_region(
    name: Annotated[str, typer.Option("--name", "-n", help="Nome da região.")],
    slug: Annotated[
        str | None, typer.Option(help="Slug; gerado pelo nome quando omitido.")
    ] = None,
    description: Annotated[str, typer.Option("--description", "-d")] = "",
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    execute(
        lambda: make_service(RegionsService).create(
            AddRegion(name=name, slug=slug, description=description)
        ),
        output=output,
        title="Região criada",
    )


app.command("post", help="Cria uma região.")(post_region)
app.command("create", hidden=True)(post_region)


@app.command("view")
def view_region(
    region_id: Annotated[int, typer.Argument(min=1)],
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Exibe uma região pelo ID."""
    execute(
        lambda: make_service(RegionsService).get(region_id),
        output=output,
        title="Região",
    )


@app.command("list")
def list_regions(
    search: Annotated[str | None, typer.Option("--search", "-s")] = None,
    limit: Annotated[int | None, typer.Option(min=0)] = None,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Lista regiões, opcionalmente filtradas."""
    execute(
        lambda: make_service(RegionsService).list(search=search, limit=limit),
        output=output,
        title="Regiões",
    )


@app.command("delete")
def delete_region(
    region_id: Annotated[int, typer.Argument(min=1)],
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Exclui uma região pelo ID."""

    def operation() -> dict[str, object]:
        make_service(RegionsService).delete(region_id)
        return {"deleted": True, "resource": "region", "id": region_id}

    execute(operation, output=output, title="Região removida")
