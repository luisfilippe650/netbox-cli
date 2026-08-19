from typing import Annotated

import typer

from netbox_cli.cli.common import execute, make_service
from netbox_cli.presentation.output import OutputFormat
from netbox_cli.schemas.devices import AddDeviceType
from netbox_cli.service.devices import DeviceTypesService

app = typer.Typer(help="Gerencia tipos de dispositivos.", no_args_is_help=True)


@app.command("post")
def post_device_type(
    manufacturer: Annotated[int, typer.Option("--manufacturer", min=1)],
    model: Annotated[str, typer.Option("--model")],
    u_height: Annotated[float, typer.Option("--u-height", min=0)],
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Adiciona um tipo de dispositivo."""
    execute(
        lambda: make_service(DeviceTypesService).create(
            AddDeviceType(
                manufacturer=manufacturer,
                model=model,
                u_height=u_height,
            )
        ),
        output=output,
        title="Tipo de dispositivo criado",
    )


@app.command("get")
def get_device_type(
    device_type_id: Annotated[int, typer.Argument(min=1)],
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Obtém um tipo de dispositivo pelo ID."""
    execute(
        lambda: make_service(DeviceTypesService).get(device_type_id),
        output=output,
        title="Tipo de dispositivo",
    )


@app.command("all")
def all_device_types(
    search: Annotated[str | None, typer.Option("--search", "-s")] = None,
    limit: Annotated[int | None, typer.Option(min=0)] = None,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Lista tipos de dispositivos."""
    execute(
        lambda: make_service(DeviceTypesService).list(search=search, limit=limit),
        output=output,
        title="Tipos de dispositivos",
    )


app.command("list", hidden=True)(all_device_types)


@app.command("delete")
def delete_device_type(
    device_type_id: Annotated[int, typer.Argument(min=1)],
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Exclui um tipo de dispositivo pelo ID."""

    def operation() -> dict[str, object]:
        make_service(DeviceTypesService).delete(device_type_id)
        return {"deleted": True, "resource": "device-type", "id": device_type_id}

    execute(operation, output=output, title="Tipo de dispositivo removido")
