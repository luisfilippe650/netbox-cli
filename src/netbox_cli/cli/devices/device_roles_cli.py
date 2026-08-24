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
from netbox_cli.schemas.devices import AddDeviceRole, UpdateDeviceRole
from netbox_cli.service.devices import DeviceRolesService

app = typer.Typer(help="Gerencia funções de dispositivos.", no_args_is_help=True)


@app.command("create")
def create_device_role(
    ctx: typer.Context,
    name: Annotated[str, typer.Option("--name", "-n", help="Nome da função.")],
    color: Annotated[
        str, typer.Option("--color", help="Cor hexadecimal sem #.")
    ] = "9e9e9e",
    vm_role: Annotated[
        bool,
        typer.Option(
            "--vm-role/--no-vm-role",
            help="Permite usar a função também em máquinas virtuais.",
        ),
    ] = True,
    description: Annotated[str, typer.Option("--description")] = "",
    ensure: Annotated[
        bool, typer.Option("--ensure", help="Cria ou converge pelo nome.")
    ] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Cria uma função de dispositivo."""
    execute(
        lambda: create_resource(
            DeviceRolesService,
            AddDeviceRole(
                name=name,
                color=color,
                vm_role=vm_role,
                description=description,
            ),
            ensure=ensure,
            dry_run=dry_run,
            update_fields=explicit_update_fields(
                ctx,
                required={"name"},
                optional={"color", "vm_role", "description"},
            ),
        ),
        output=output,
        title="Função de dispositivo criada",
    )


@app.command("list")
def list_device_roles(
    search: Annotated[str | None, typer.Option("--search", "-s")] = None,
    limit: Annotated[int | None, typer.Option(min=0)] = 0,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Lista funções de dispositivos."""
    execute(
        lambda: make_service(DeviceRolesService).list(search=search, limit=limit),
        output=output,
        title="Funções de dispositivos",
    )


@app.command("get")
def get_device_role(
    role_id: Annotated[int, typer.Argument(min=1)],
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Obtém uma função de dispositivo pelo ID."""
    execute(
        lambda: make_service(DeviceRolesService).get(role_id),
        output=output,
        title="Função de dispositivo",
    )


@app.command("update")
def update_device_role(
    role_id: Annotated[int, typer.Argument(min=1)],
    name: Annotated[str | None, typer.Option("--name", "-n")] = None,
    color: Annotated[
        str | None, typer.Option("--color", help="Cor hexadecimal sem #.")
    ] = None,
    vm_role: Annotated[
        bool | None,
        typer.Option(
            "--vm-role/--no-vm-role",
            help="Permite ou impede o uso em máquinas virtuais.",
        ),
    ] = None,
    description: Annotated[str | None, typer.Option("--description")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Atualiza somente os campos informados de uma função."""
    execute(
        lambda: update_resource(
            DeviceRolesService,
            role_id,
            UpdateDeviceRole(
                name=name,
                color=color,
                vm_role=vm_role,
                description=description,
            ),
            dry_run=dry_run,
        ),
        output=output,
        title="Função de dispositivo atualizada",
    )


@app.command("delete")
def delete_device_role(
    role_id: Annotated[int, typer.Argument(min=1)],
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    ignore_not_found: Annotated[bool, typer.Option("--ignore-not-found")] = False,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Exclui uma função de dispositivo pelo ID."""
    execute(
        lambda: delete_resource(
            DeviceRolesService,
            role_id,
            resource="device-role",
            dry_run=dry_run,
            ignore_not_found=ignore_not_found,
        ),
        output=output,
        title="Função de dispositivo removida",
    )


app.command("post", hidden=True)(create_device_role)
app.command("all", hidden=True)(list_device_roles)
