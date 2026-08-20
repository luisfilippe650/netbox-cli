from typing import Annotated

import typer

from netbox_cli.cli.common import (
    create_resource,
    delete_resource,
    execute,
    execute_operation,
    explicit_update_fields,
    make_service,
    parse_json_object,
)
from netbox_cli.presentation.details import (
    DetailOutputFormat,
    render_infrastructure_tree,
    render_inspection,
)
from netbox_cli.presentation.output import is_json_output, render_json
from netbox_cli.presentation.output import OutputFormat
from netbox_cli.schemas.devices import AddDevice
from netbox_cli.service.devices import DevicesService
from netbox_cli.service.infrastructure_service import InfrastructureService

app = typer.Typer(help="Gerencia dispositivos.", no_args_is_help=True)


@app.command("post")
def post_device(
    ctx: typer.Context,
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
    ensure: Annotated[
        bool, typer.Option("--ensure", help="Converge nome dentro do site.")
    ] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Adiciona um dispositivo; o status é active e a face montada é front."""
    execute(
        lambda: create_resource(
            DevicesService,
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
            ),
            ensure=ensure,
            dry_run=dry_run,
            filters={"site_id": site},
            update_fields=explicit_update_fields(
                ctx,
                required={"name", "role", "device_type", "site"},
                optional={
                    "serial": "serial",
                    "location": "location",
                    "rack": "rack",
                    "position": "position",
                    "custom_fields": "custom_fields",
                },
            )
            | ({"face"} if position is not None else set()),
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
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    ignore_not_found: Annotated[bool, typer.Option("--ignore-not-found")] = False,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Exclui um dispositivo pelo ID."""

    execute(
        lambda: delete_resource(
            DevicesService,
            device_id,
            resource="device",
            dry_run=dry_run,
            ignore_not_found=ignore_not_found,
        ),
        output=output,
        title="Dispositivo removido",
    )


@app.command("move")
def move_device(
    name: Annotated[str, typer.Argument(help="Nome exato do dispositivo.")],
    rack: Annotated[str, typer.Option("--rack", help="Nome exato do rack de destino.")],
    position: Annotated[float, typer.Option("--position", min=1)],
    device_site: Annotated[str | None, typer.Option("--device-site")] = None,
    rack_site: Annotated[str | None, typer.Option("--rack-site")] = None,
    rack_location: Annotated[str | None, typer.Option("--rack-location")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
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
            dry_run=dry_run,
        )
    )
    if is_json_output(output):
        render_json(result)
    else:
        verb = "seria movido" if result.get("dry_run") else "movido"
        typer.echo(
            f"{result['device']} {verb} para {result['rack']} "
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


@app.command("tree")
def device_tree(
    name: Annotated[str, typer.Argument(help="Nome exato do dispositivo.")],
    site: Annotated[str | None, typer.Option("--site")] = None,
    output: Annotated[
        DetailOutputFormat, typer.Option("--output", "-o")
    ] = DetailOutputFormat.human,
) -> None:
    """Exibe localização, interfaces, IPs e conexões de um dispositivo."""
    result = execute_operation(
        lambda: make_service(InfrastructureService).device_tree(
            name,
            site_name=site,
        )
    )
    render_infrastructure_tree(result, output)


@app.command("allocate")
def allocate_device(
    name: Annotated[str, typer.Argument(help="Nome exato do dispositivo.")],
    rack: Annotated[str, typer.Option("--rack", help="Rack de destino.")],
    position: Annotated[float, typer.Option("--position", min=1)],
    device_site: Annotated[str | None, typer.Option("--device-site")] = None,
    rack_site: Annotated[str | None, typer.Option("--rack-site")] = None,
    rack_location: Annotated[str | None, typer.Option("--rack-location")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
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
            dry_run=dry_run,
        )
    )
    if is_json_output(output):
        render_json(result)
    else:
        verb = "seria alocado" if result.get("dry_run") else "alocado"
        typer.echo(
            f"{result['device']} {verb} em {result['rack']} "
            f"na posição U{result['position']}."
        )


@app.command("deallocate")
def deallocate_device(
    name: Annotated[str, typer.Argument(help="Nome exato do dispositivo.")],
    site: Annotated[str | None, typer.Option("--site")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    output: Annotated[
        DetailOutputFormat, typer.Option("--output", "-o")
    ] = DetailOutputFormat.human,
) -> None:
    """Retira um dispositivo do rack, preservando seu site e local."""
    result = execute_operation(
        lambda: make_service(DevicesService).deallocate(
            name, site_name=site, dry_run=dry_run
        )
    )
    if is_json_output(output):
        render_json(result)
    else:
        verb = "seria desalocado" if result.get("dry_run") else "desalocado"
        typer.echo(
            f"{result['device']} {verb} de "
            f"{result.get('previous_rack') or 'nenhum rack'}."
        )
