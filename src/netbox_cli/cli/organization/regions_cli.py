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
from netbox_cli.schemas.organization.regions_dto import AddRegion, UpdateRegion
from netbox_cli.service.organization.regions_service import RegionsService

app = typer.Typer(help="Gerencia regiões do NetBox.", no_args_is_help=True)


def post_region(
    ctx: typer.Context,
    name: Annotated[str, typer.Option("--name", "-n", help="Nome da região.")],
    slug: Annotated[
        str | None, typer.Option(help="Slug; gerado pelo nome quando omitido.")
    ] = None,
    description: Annotated[str, typer.Option("--description", "-d")] = "",
    ensure: Annotated[bool, typer.Option("--ensure", help="Cria ou converge pelo nome.")] = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Mostra a mudança sem aplicá-la.")
    ] = False,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    execute(
        lambda: create_resource(
            RegionsService,
            AddRegion(name=name, slug=slug, description=description),
            ensure=ensure,
            dry_run=dry_run,
            update_fields=explicit_update_fields(
                ctx,
                required={"name"},
                optional={"slug", "description"},
            ),
        ),
        output=output,
        title="Região criada",
    )


app.command("create", help="Cria uma região.")(post_region)
app.command("post", hidden=True)(post_region)


@app.command("get")
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


app.command("view", hidden=True)(view_region)


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


@app.command("update")
def update_region(
    region_id: Annotated[int, typer.Argument(min=1)],
    name: Annotated[str | None, typer.Option("--name", "-n")] = None,
    slug: Annotated[str | None, typer.Option("--slug")] = None,
    description: Annotated[str | None, typer.Option("--description", "-d")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Atualiza somente os campos informados de uma região."""
    execute(
        lambda: update_resource(
            RegionsService,
            region_id,
            UpdateRegion(name=name, slug=slug, description=description),
            dry_run=dry_run,
        ),
        output=output,
        title="Região atualizada",
    )


@app.command("delete")
def delete_region(
    region_id: Annotated[int, typer.Argument(min=1)],
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    ignore_not_found: Annotated[bool, typer.Option("--ignore-not-found")] = False,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Exclui uma região pelo ID."""

    execute(
        lambda: delete_resource(
            RegionsService,
            region_id,
            resource="region",
            dry_run=dry_run,
            ignore_not_found=ignore_not_found,
        ),
        output=output,
        title="Região removida",
    )
