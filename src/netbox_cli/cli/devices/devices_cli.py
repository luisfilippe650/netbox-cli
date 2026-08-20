from typing import Annotated

import typer

from netbox_cli.cli.common import execute, execute_operation, make_service, parse_json_object
from netbox_cli.presentation.details import DetailOutputFormat, render_inspection
from netbox_cli.presentation.output import render_json
from netbox_cli.presentation.output import OutputFormat
from netbox_cli.schemas.devices import AddDevice
from netbox_cli.service.devices import DevicesService

app = typer.Typer(help="Gerencia dispositivos.", no_args_is_help=True)


@app.command("post")
def post_device(
    name: Annotated[str, typer.Option("--name", "-n")],
    role: Annotated[int, typer.Option("--role", help="ID da função.", min=1)],
    device_type: Annotated[int, typer.Option("--device-type", help="ID do tipo.", min=1)],
    site: Annotated[int, typer.Option("--site", help="ID do site.", min=1)],
    serial: Annotated[str | None, typer.Option("--serial")] = None,
    location: Annotated[int | None, typer.Option("--location", min=1)] = None,
    rack: Annotated[int | None, typer.Option("--rack", min=1)] = None,
    position: Annotated[float | None, typer.Option("--position", min=1)] = None,
    custom_fields: Annotated[
        str,
        typer.Option(
            "--custom-fields",
            help='Objeto JSON, por exemplo: {"patrimonio":"123"}.',
        ),
    ] = "{}",
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Adiciona um dispositivo; o status é active e a face montada é front."""
    execute(
        lambda: make_service(DevicesService).create(
            AddDevice(
                name=name,
                role=role,
                device_type=device_type,
                site=site,
                serial=serial,
                location=location,
                rack=rack,
                position=position,
                custom_fields=parse_json_object(
                    custom_fields, option_name="--custom-fields"
                ),
            )
        ),
        output=output,
        title="Dispositivo criado",
    )


@app.command("get")
def get_device(
    device_id: Annotated[int, typer.Argument(min=1)],
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Obtém um dispositivo pelo ID."""
    execute(
        lambda: make_service(DevicesService).get(device_id),
        output=output,
        title="Dispositivo",
    )


@app.command("all")
def all_devices(
    search: Annotated[str | None, typer.Option("--search", "-s")] = None,
    limit: Annotated[int | None, typer.Option(min=0)] = 0,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Lista dispositivos."""
    execute(
        lambda: make_service(DevicesService).list(search=search, limit=limit),
        output=output,
        title="Dispositivos",
    )


app.command("list", hidden=True)(all_devices)


@app.command("delete")
def delete_device(
    device_id: Annotated[int, typer.Argument(min=1)],
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Exclui um dispositivo pelo ID."""

    def operation() -> dict[str, object]:
        make_service(DevicesService).delete(device_id)
        return {"deleted": True, "resource": "device", "id": device_id}

    execute(operation, output=output, title="Dispositivo removido")


@app.command("move")
def move_device(
    name: Annotated[str, typer.Argument(help="Nome exato do dispositivo.")],
    rack: Annotated[str, typer.Option("--rack", help="Nome exato do rack de destino.")],
    position: Annotated[float, typer.Option("--position", min=1)],
    device_site: Annotated[str | None, typer.Option("--device-site")] = None,
    rack_site: Annotated[str | None, typer.Option("--rack-site")] = None,
    rack_location: Annotated[str | None, typer.Option("--rack-location")] = None,
    output: Annotated[
        DetailOutputFormat, typer.Option("--output", "-o")
    ] = DetailOutputFormat.human,
) -> None:
    """Move um dispositivo para um rack e posição, na face frontal."""
    result = execute_operation(
        lambda: make_service(DevicesService).move(
            name,
            rack_name=rack,
            position=position,
            device_site_name=device_site,
            rack_site_name=rack_site,
            rack_location_name=rack_location,
        )
    )
    if output is DetailOutputFormat.json:
        render_json(result)
    else:
        typer.echo(
            f"{result['device']} movido para {result['rack']} "
            f"na posição U{result['position']}."
        )


@app.command("inspect")
def inspect_device(
    name: Annotated[str, typer.Argument(help="Nome exato do dispositivo.")],
    site: Annotated[str | None, typer.Option("--site")] = None,
    output: Annotated[
        DetailOutputFormat, typer.Option("--output", "-o")
    ] = DetailOutputFormat.human,
) -> None:
    """Exibe a visão completa de um dispositivo."""
    result = execute_operation(
        lambda: make_service(DevicesService).inspect(name, site_name=site)
    )
    render_inspection(result, output)


@app.command("allocate")
def allocate_device(
    name: Annotated[str, typer.Argument(help="Nome exato do dispositivo.")],
    rack: Annotated[str, typer.Option("--rack", help="Rack de destino.")],
    position: Annotated[float, typer.Option("--position", min=1)],
    device_site: Annotated[str | None, typer.Option("--device-site")] = None,
    rack_site: Annotated[str | None, typer.Option("--rack-site")] = None,
    rack_location: Annotated[str | None, typer.Option("--rack-location")] = None,
    output: Annotated[
        DetailOutputFormat, typer.Option("--output", "-o")
    ] = DetailOutputFormat.human,
) -> None:
    """Aloca um dispositivo em um rack e posição."""
    result = execute_operation(
        lambda: make_service(DevicesService).allocate(
            name,
            rack_name=rack,
            position=position,
            device_site_name=device_site,
            rack_site_name=rack_site,
            rack_location_name=rack_location,
        )
    )
    if output is DetailOutputFormat.json:
        render_json(result)
    else:
        typer.echo(
            f"{result['device']} alocado em {result['rack']} "
            f"na posição U{result['position']}."
        )


@app.command("deallocate")
def deallocate_device(
    name: Annotated[str, typer.Argument(help="Nome exato do dispositivo.")],
    site: Annotated[str | None, typer.Option("--site")] = None,
    output: Annotated[
        DetailOutputFormat, typer.Option("--output", "-o")
    ] = DetailOutputFormat.human,
) -> None:
    """Retira um dispositivo do rack, preservando seu site e local."""
    result = execute_operation(
        lambda: make_service(DevicesService).deallocate(name, site_name=site)
    )
    if output is DetailOutputFormat.json:
        render_json(result)
    else:
        typer.echo(
            f"{result['device']} desalocado de "
            f"{result.get('previous_rack') or 'nenhum rack'}."
        )
