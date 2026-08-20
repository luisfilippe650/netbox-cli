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
from netbox_cli.schemas.racks import AddRackGroup, UpdateRackGroup
from netbox_cli.service.racks import RackGroupsService

app = typer.Typer(help="Gerencia grupos de racks.", no_args_is_help=True)


@app.command("post")
def post_rack_group(
    ctx: typer.Context,
    name: Annotated[str, typer.Option("--name", "-n", help="Nome do grupo.")],
    ensure: Annotated[bool, typer.Option("--ensure", help="Cria ou converge pelo nome.")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Cria um grupo de racks informando somente o nome."""
    execute(
        lambda: create_resource(
            RackGroupsService,
            AddRackGroup(name=name),
            ensure=ensure,
            dry_run=dry_run,
            update_fields=explicit_update_fields(
                ctx,
                required={"name"},
                optional=set(),
            ),
        ),
        output=output,
        title="Grupo de racks criado",
    )


@app.command("get")
def get_rack_group(
    group_id: Annotated[int, typer.Argument(min=1)],
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Obtém um grupo de racks pelo ID."""
    execute(
        lambda: make_service(RackGroupsService).get(group_id),
        output=output,
        title="Grupo de racks",
    )


@app.command("all")
def all_rack_groups(
    search: Annotated[str | None, typer.Option("--search", "-s")] = None,
    limit: Annotated[int | None, typer.Option(min=0)] = 0,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Lista todos os grupos de racks."""
    execute(
        lambda: make_service(RackGroupsService).list(search=search, limit=limit),
        output=output,
        title="Grupos de racks",
    )


@app.command("update")
def update_rack_group(
    group_id: Annotated[int, typer.Argument(min=1)],
    name: Annotated[str, typer.Option("--name", "-n", help="Novo nome do grupo.")],
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Atualiza o nome de um grupo de racks."""
    execute(
        lambda: update_resource(
            RackGroupsService,
            group_id,
            UpdateRackGroup(name=name),
            dry_run=dry_run,
        ),
        output=output,
        title="Grupo de racks atualizado",
    )


@app.command("delete")
def delete_rack_group(
    group_id: Annotated[int, typer.Argument(min=1)],
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    ignore_not_found: Annotated[bool, typer.Option("--ignore-not-found")] = False,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Exclui um grupo de racks pelo ID."""

    execute(
        lambda: delete_resource(
            RackGroupsService,
            group_id,
            resource="rack-group",
            dry_run=dry_run,
            ignore_not_found=ignore_not_found,
        ),
        output=output,
        title="Grupo de racks removido",
    )
