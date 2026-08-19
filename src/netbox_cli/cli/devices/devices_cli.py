from typing import Annotated

import typer

from netbox_cli.cli.common import execute, make_service, parse_json_object
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
    limit: Annotated[int | None, typer.Option(min=0)] = None,
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
