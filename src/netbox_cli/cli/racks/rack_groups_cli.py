from typing import Annotated

import typer

from netbox_cli.cli.common import execute, make_service
from netbox_cli.presentation.output import OutputFormat
from netbox_cli.schemas.racks import AddRackGroup, UpdateRackGroup
from netbox_cli.service.racks import RackGroupsService

app = typer.Typer(help="Gerencia grupos de racks.", no_args_is_help=True)


@app.command("post")
def post_rack_group(
    name: Annotated[str, typer.Option("--name", "-n", help="Nome do grupo.")],
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Cria um grupo de racks informando somente o nome."""
    execute(
        lambda: make_service(RackGroupsService).create(AddRackGroup(name=name)),
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
    limit: Annotated[int | None, typer.Option(min=0)] = None,
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
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Atualiza o nome de um grupo de racks."""
    execute(
        lambda: make_service(RackGroupsService).update(
            group_id, UpdateRackGroup(name=name)
        ),
        output=output,
        title="Grupo de racks atualizado",
    )


@app.command("delete")
def delete_rack_group(
    group_id: Annotated[int, typer.Argument(min=1)],
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Exclui um grupo de racks pelo ID."""

    def operation() -> dict[str, object]:
        make_service(RackGroupsService).delete(group_id)
        return {"deleted": True, "resource": "rack-group", "id": group_id}

    execute(operation, output=output, title="Grupo de racks removido")
