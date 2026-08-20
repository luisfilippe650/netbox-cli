from typing import Annotated

import typer

from netbox_cli.cli.common import (
    create_resource,
    delete_resource,
    execute,
    explicit_update_fields,
    make_service,
)
from netbox_cli.presentation.output import OutputFormat
from netbox_cli.schemas.devices import AddDeviceType
from netbox_cli.service.devices import DeviceTypesService

app = typer.Typer(help="Gerencia tipos de dispositivos.", no_args_is_help=True)


@app.command("post")
def post_device_type(
    ctx: typer.Context,
    manufacturer: Annotated[int, typer.Option("--manufacturer", min=1)],
    model: Annotated[str, typer.Option("--model")],
    u_height: Annotated[float, typer.Option("--u-height", min=0)],
    ensure: Annotated[
        bool, typer.Option("--ensure", help="Converge modelo por fabricante.")
    ] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Adiciona um tipo de dispositivo."""
    execute(
        lambda: create_resource(
            DeviceTypesService,
            AddDeviceType(
                manufacturer=manufacturer,
                model=model,
                u_height=u_height,
            ),
            ensure=ensure,
            dry_run=dry_run,
            identity_field="model",
            filters={"manufacturer_id": manufacturer},
            update_fields=explicit_update_fields(
                ctx,
                required={"manufacturer", "model", "u_height"},
                optional=set(),
            ),
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
    limit: Annotated[int | None, typer.Option(min=0)] = 0,
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
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    ignore_not_found: Annotated[bool, typer.Option("--ignore-not-found")] = False,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Exclui um tipo de dispositivo pelo ID."""

    execute(
        lambda: delete_resource(
            DeviceTypesService,
            device_type_id,
            resource="device-type",
            dry_run=dry_run,
            ignore_not_found=ignore_not_found,
        ),
        output=output,
        title="Tipo de dispositivo removido",
    )
