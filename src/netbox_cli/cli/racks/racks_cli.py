from typing import Annotated

import typer

from netbox_cli.cli.common import execute, execute_operation, make_service
from netbox_cli.presentation.details import (
    DetailOutputFormat,
    render_availability,
    render_capacity,
    render_rack,
)
from netbox_cli.presentation.output import OutputFormat
from netbox_cli.schemas.racks import AddRack, UpdateRack
from netbox_cli.service.racks import RacksService

app = typer.Typer(help="Gerencia racks.", no_args_is_help=True)


@app.command("post")
def post_rack(
    site: Annotated[int, typer.Option("--site", help="ID do site.", min=1)],
    name: Annotated[str, typer.Option("--name", "-n", help="Nome do rack.")],
    width: Annotated[int, typer.Option("--width", help="Largura: 10, 19, 21 ou 23.")],
    starting_unit: Annotated[int, typer.Option("--starting-unit", min=1)],
    u_height: Annotated[int, typer.Option("--u-height", min=1)],
    group: Annotated[int | None, typer.Option("--group", min=1)] = None,
    role: Annotated[
        int | None, typer.Option("--role", "--function", help="ID da função.", min=1)
    ] = None,
    rack_type: Annotated[
        int | None, typer.Option("--type", "--rack-type", help="ID do tipo.", min=1)
    ] = None,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Cria um rack; o status é definido automaticamente como active."""
    execute(
        lambda: make_service(RacksService).create(
            AddRack(
                site=site,
                name=name,
                width=width,
                starting_unit=starting_unit,
                u_height=u_height,
                group=group,
                role=role,
                rack_type=rack_type,
            )
        ),
        output=output,
        title="Rack criado",
    )


@app.command("get")
def get_rack(
    rack_id: Annotated[int, typer.Argument(min=1)],
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Obtém um rack pelo ID."""
    execute(
        lambda: make_service(RacksService).get(rack_id), output=output, title="Rack"
    )


@app.command("all")
def all_racks(
    search: Annotated[str | None, typer.Option("--search", "-s")] = None,
    limit: Annotated[int | None, typer.Option(min=0)] = None,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Lista todos os racks."""
    execute(
        lambda: make_service(RacksService).list(search=search, limit=limit),
        output=output,
        title="Racks",
    )


@app.command("update")
def update_rack(
    rack_id: Annotated[int, typer.Argument(min=1)],
    site: Annotated[int | None, typer.Option("--site", min=1)] = None,
    name: Annotated[str | None, typer.Option("--name", "-n")] = None,
    width: Annotated[int | None, typer.Option("--width")] = None,
    starting_unit: Annotated[int | None, typer.Option("--starting-unit", min=1)] = None,
    u_height: Annotated[int | None, typer.Option("--u-height", min=1)] = None,
    group: Annotated[int | None, typer.Option("--group", min=1)] = None,
    role: Annotated[int | None, typer.Option("--role", "--function", min=1)] = None,
    rack_type: Annotated[
        int | None, typer.Option("--type", "--rack-type", min=1)
    ] = None,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Atualiza somente os campos informados de um rack."""
    execute(
        lambda: make_service(RacksService).update(
            rack_id,
            UpdateRack(
                site=site,
                name=name,
                width=width,
                starting_unit=starting_unit,
                u_height=u_height,
                group=group,
                role=role,
                rack_type=rack_type,
            ),
        ),
        output=output,
        title="Rack atualizado",
    )


@app.command("delete")
def delete_rack(
    rack_id: Annotated[int, typer.Argument(min=1)],
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Exclui um rack pelo ID."""

    def operation() -> dict[str, object]:
        make_service(RacksService).delete(rack_id)
        return {"deleted": True, "resource": "rack", "id": rack_id}

    execute(operation, output=output, title="Rack removido")


@app.command("show")
def show_rack(
    name: Annotated[str, typer.Argument(help="Nome exato do rack.")],
    site: Annotated[str | None, typer.Option("--site")] = None,
    location: Annotated[str | None, typer.Option("--location")] = None,
    face: Annotated[
        str, typer.Option("--face", help="Face do rack: front ou rear.")
    ] = "front",
    output: Annotated[
        DetailOutputFormat, typer.Option("--output", "-o")
    ] = DetailOutputFormat.human,
) -> None:
    """Desenha a elevação de um rack."""
    if face not in {"front", "rear"}:
        raise typer.BadParameter("use 'front' ou 'rear'", param_hint="--face")
    result = execute_operation(
        lambda: make_service(RacksService).elevation(
            name, face=face, site_name=site, location_name=location
        )
    )
    render_rack(result, output)


@app.command("available")
def available_rack_positions(
    name: Annotated[str, typer.Argument(help="Nome exato do rack.")],
    height: Annotated[float, typer.Option("--height", min=0.5)],
    site: Annotated[str | None, typer.Option("--site")] = None,
    location: Annotated[str | None, typer.Option("--location")] = None,
    face: Annotated[
        str, typer.Option("--face", help="Face do rack: front ou rear.")
    ] = "front",
    output: Annotated[
        DetailOutputFormat, typer.Option("--output", "-o")
    ] = DetailOutputFormat.human,
) -> None:
    """Lista posições contíguas disponíveis para um equipamento."""
    if face not in {"front", "rear"}:
        raise typer.BadParameter("use 'front' ou 'rear'", param_hint="--face")
    result = execute_operation(
        lambda: make_service(RacksService).available(
            name,
            height=height,
            face=face,
            site_name=site,
            location_name=location,
        )
    )
    render_availability(result, output)


@app.command("capacity")
def rack_capacity(
    name: Annotated[str, typer.Argument(help="Nome exato do rack.")],
    site: Annotated[str | None, typer.Option("--site")] = None,
    location: Annotated[str | None, typer.Option("--location")] = None,
    output: Annotated[
        DetailOutputFormat, typer.Option("--output", "-o")
    ] = DetailOutputFormat.human,
) -> None:
    """Mostra capacidade e ocupação física do rack por face."""
    result = execute_operation(
        lambda: make_service(RacksService).capacity(
            name, site_name=site, location_name=location
        )
    )
    render_capacity(result, output)
