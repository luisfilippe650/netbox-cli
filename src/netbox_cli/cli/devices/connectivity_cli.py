from typing import Annotated, Any

import typer

from netbox_cli.cli.common import (
    create_resource,
    delete_resource,
    execute,
    make_service,
    update_resource,
)
from netbox_cli.presentation.output import OutputFormat
from netbox_cli.schemas.devices import (
    AddCable,
    AddConsolePort,
    AddFrontPort,
    AddInterface,
    AddPowerPort,
    AddRearPort,
    TerminationType,
    UpdateCable,
    UpdateConsolePort,
    UpdateFrontPort,
    UpdateInterface,
    UpdatePowerPort,
    UpdateRearPort,
)
from netbox_cli.service.devices import (
    CablesService,
    ConsolePortsService,
    FrontPortsService,
    InterfacesService,
    PowerPortsService,
    RearPortsService,
)

interfaces_app = typer.Typer(help="Gerencia interfaces de dispositivos.", no_args_is_help=True)
front_ports_app = typer.Typer(help="Gerencia portas frontais.", no_args_is_help=True)
rear_ports_app = typer.Typer(help="Gerencia portas traseiras.", no_args_is_help=True)
console_ports_app = typer.Typer(help="Gerencia portas de console.", no_args_is_help=True)
power_ports_app = typer.Typer(help="Gerencia portas de energia.", no_args_is_help=True)
cables_app = typer.Typer(help="Gerencia cabos e conexões.", no_args_is_help=True)


def _register_get_command(
    command_app: typer.Typer,
    service_class: type[Any],
    *,
    title: str,
) -> None:
    @command_app.command("get")
    def get_component(
        component_id: Annotated[int, typer.Argument(min=1)],
        output: Annotated[
            OutputFormat, typer.Option("--output", "-o")
        ] = OutputFormat.json,
    ) -> None:
        """Obtém um recurso pelo ID."""
        execute(
            lambda: make_service(service_class).get(component_id),
            output=output,
            title=title,
        )


_register_get_command(interfaces_app, InterfacesService, title="Interface")
_register_get_command(front_ports_app, FrontPortsService, title="Porta frontal")
_register_get_command(rear_ports_app, RearPortsService, title="Porta traseira")
_register_get_command(console_ports_app, ConsolePortsService, title="Porta de console")
_register_get_command(power_ports_app, PowerPortsService, title="Porta de energia")
_register_get_command(cables_app, CablesService, title="Cabo")


def _list_components(
    service_class: type[Any],
    *,
    device: str | None,
    search: str | None,
    limit: int | None,
) -> Any:
    return make_service(service_class).list(
        device=device,
        search=search,
        limit=limit,
    )


def _delete_component(
    service_class: type[Any],
    component_id: int,
    *,
    resource: str,
    dry_run: bool,
    ignore_not_found: bool,
) -> Any:
    return delete_resource(
        service_class,
        component_id,
        resource=resource,
        dry_run=dry_run,
        ignore_not_found=ignore_not_found,
    )


@interfaces_app.command("create")
def create_interface(
    device: Annotated[str, typer.Option("--device", help="ID ou nome exato do dispositivo.")],
    name: Annotated[str, typer.Option("--name", "-n")],
    interface_type: Annotated[
        str, typer.Option("--type", help="Tipo NetBox, por exemplo 1000base-t.")
    ],
    label: Annotated[str, typer.Option("--label")] = "",
    enabled: Annotated[bool, typer.Option("--enabled/--disabled")] = True,
    mtu: Annotated[int | None, typer.Option("--mtu", min=1)] = None,
    mgmt_only: Annotated[bool, typer.Option("--mgmt-only/--not-mgmt-only")] = False,
    description: Annotated[str, typer.Option("--description")] = "",
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Cria uma interface em um dispositivo."""
    execute(
        lambda: create_resource(
            InterfacesService,
            AddInterface(
                device=device,
                name=name,
                type=interface_type,
                label=label,
                enabled=enabled,
                mtu=mtu,
                mgmt_only=mgmt_only,
                description=description,
            ),
            dry_run=dry_run,
        ),
        output=output,
        title="Interface criada",
    )


@interfaces_app.command("list")
def list_interfaces(
    device: Annotated[str | None, typer.Option("--device")] = None,
    search: Annotated[str | None, typer.Option("--search", "-s")] = None,
    limit: Annotated[int | None, typer.Option(min=0)] = 0,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Lista interfaces, opcionalmente por dispositivo."""
    execute(
        lambda: _list_components(InterfacesService, device=device, search=search, limit=limit),
        output=output,
        title="Interfaces",
    )


@interfaces_app.command("update")
def update_interface(
    interface_id: Annotated[int, typer.Argument(min=1)],
    name: Annotated[str | None, typer.Option("--name", "-n")] = None,
    interface_type: Annotated[str | None, typer.Option("--type")] = None,
    label: Annotated[str | None, typer.Option("--label")] = None,
    enabled: Annotated[bool | None, typer.Option("--enabled/--disabled")] = None,
    mtu: Annotated[int | None, typer.Option("--mtu", min=1)] = None,
    mgmt_only: Annotated[bool | None, typer.Option("--mgmt-only/--not-mgmt-only")] = None,
    description: Annotated[str | None, typer.Option("--description")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Atualiza uma interface pelo ID."""
    execute(
        lambda: update_resource(
            InterfacesService,
            interface_id,
            UpdateInterface(
                name=name,
                type=interface_type,
                label=label,
                enabled=enabled,
                mtu=mtu,
                mgmt_only=mgmt_only,
                description=description,
            ),
            dry_run=dry_run,
        ),
        output=output,
        title="Interface atualizada",
    )


@interfaces_app.command("delete")
def delete_interface(
    interface_id: Annotated[int, typer.Argument(min=1)],
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    ignore_not_found: Annotated[bool, typer.Option("--ignore-not-found")] = False,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Exclui uma interface pelo ID."""
    execute(
        lambda: _delete_component(
            InterfacesService,
            interface_id,
            resource="interface",
            dry_run=dry_run,
            ignore_not_found=ignore_not_found,
        ),
        output=output,
        title="Interface removida",
    )


@rear_ports_app.command("create")
def create_rear_port(
    device: Annotated[str, typer.Option("--device", help="ID ou nome exato do dispositivo.")],
    name: Annotated[str, typer.Option("--name", "-n")],
    port_type: Annotated[str, typer.Option("--type", help="Tipo NetBox, por exemplo 8p8c ou lc.")],
    positions: Annotated[int, typer.Option("--positions", min=1)] = 1,
    color: Annotated[str, typer.Option("--color", help="Cor hexadecimal sem #.")] = "",
    description: Annotated[str, typer.Option("--description")] = "",
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Cria uma porta traseira."""
    execute(
        lambda: create_resource(
            RearPortsService,
            AddRearPort(
                device=device,
                name=name,
                type=port_type,
                positions=positions,
                color=color,
                description=description,
            ),
            dry_run=dry_run,
        ),
        output=output,
        title="Porta traseira criada",
    )


@rear_ports_app.command("list")
def list_rear_ports(
    device: Annotated[str | None, typer.Option("--device")] = None,
    search: Annotated[str | None, typer.Option("--search", "-s")] = None,
    limit: Annotated[int | None, typer.Option(min=0)] = 0,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Lista portas traseiras."""
    execute(
        lambda: _list_components(
            RearPortsService, device=device, search=search, limit=limit
        ),
        output=output,
        title="Portas traseiras",
    )


@rear_ports_app.command("update")
def update_rear_port(
    port_id: Annotated[int, typer.Argument(min=1)],
    name: Annotated[str | None, typer.Option("--name", "-n")] = None,
    port_type: Annotated[str | None, typer.Option("--type")] = None,
    positions: Annotated[int | None, typer.Option("--positions", min=1)] = None,
    color: Annotated[str | None, typer.Option("--color")] = None,
    description: Annotated[str | None, typer.Option("--description")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Atualiza uma porta traseira pelo ID."""
    execute(
        lambda: update_resource(
            RearPortsService,
            port_id,
            UpdateRearPort(
                name=name,
                type=port_type,
                positions=positions,
                color=color,
                description=description,
            ),
            dry_run=dry_run,
        ),
        output=output,
        title="Porta traseira atualizada",
    )


@rear_ports_app.command("delete")
def delete_rear_port(
    port_id: Annotated[int, typer.Argument(min=1)],
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    ignore_not_found: Annotated[bool, typer.Option("--ignore-not-found")] = False,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Exclui uma porta traseira pelo ID."""
    execute(
        lambda: _delete_component(
            RearPortsService,
            port_id,
            resource="rear-port",
            dry_run=dry_run,
            ignore_not_found=ignore_not_found,
        ),
        output=output,
        title="Porta traseira removida",
    )


@front_ports_app.command("create")
def create_front_port(
    device: Annotated[str, typer.Option("--device", help="ID ou nome exato do dispositivo.")],
    name: Annotated[str, typer.Option("--name", "-n")],
    port_type: Annotated[str, typer.Option("--type")],
    rear_port: Annotated[
        str | None,
        typer.Option(
            "--rear-port",
            help="ID ou nome da porta traseira no mesmo dispositivo.",
        ),
    ] = None,
    rear_port_position: Annotated[int, typer.Option("--rear-port-position", min=1)] = 1,
    color: Annotated[str, typer.Option("--color")] = "",
    description: Annotated[str, typer.Option("--description")] = "",
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Cria uma porta frontal, opcionalmente ligada a uma traseira."""
    execute(
        lambda: create_resource(
            FrontPortsService,
            AddFrontPort(
                device=device,
                name=name,
                type=port_type,
                rear_port=rear_port,
                rear_port_position=rear_port_position,
                color=color,
                description=description,
            ),
            dry_run=dry_run,
        ),
        output=output,
        title="Porta frontal criada",
    )


@front_ports_app.command("list")
def list_front_ports(
    device: Annotated[str | None, typer.Option("--device")] = None,
    search: Annotated[str | None, typer.Option("--search", "-s")] = None,
    limit: Annotated[int | None, typer.Option(min=0)] = 0,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Lista portas frontais."""
    execute(
        lambda: _list_components(
            FrontPortsService, device=device, search=search, limit=limit
        ),
        output=output,
        title="Portas frontais",
    )


@front_ports_app.command("update")
def update_front_port(
    port_id: Annotated[int, typer.Argument(min=1)],
    name: Annotated[str | None, typer.Option("--name", "-n")] = None,
    port_type: Annotated[str | None, typer.Option("--type")] = None,
    color: Annotated[str | None, typer.Option("--color")] = None,
    description: Annotated[str | None, typer.Option("--description")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Atualiza uma porta frontal pelo ID."""
    execute(
        lambda: update_resource(
            FrontPortsService,
            port_id,
            UpdateFrontPort(
                name=name,
                type=port_type,
                color=color,
                description=description,
            ),
            dry_run=dry_run,
        ),
        output=output,
        title="Porta frontal atualizada",
    )


@front_ports_app.command("delete")
def delete_front_port(
    port_id: Annotated[int, typer.Argument(min=1)],
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    ignore_not_found: Annotated[bool, typer.Option("--ignore-not-found")] = False,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Exclui uma porta frontal pelo ID."""
    execute(
        lambda: _delete_component(
            FrontPortsService,
            port_id,
            resource="front-port",
            dry_run=dry_run,
            ignore_not_found=ignore_not_found,
        ),
        output=output,
        title="Porta frontal removida",
    )


@console_ports_app.command("create")
def create_console_port(
    device: Annotated[str, typer.Option("--device")],
    name: Annotated[str, typer.Option("--name", "-n")],
    port_type: Annotated[str | None, typer.Option("--type")] = None,
    speed: Annotated[int | None, typer.Option("--speed", min=1)] = None,
    description: Annotated[str, typer.Option("--description")] = "",
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Cria uma porta de console."""
    execute(
        lambda: create_resource(
            ConsolePortsService,
            AddConsolePort(
                device=device,
                name=name,
                type=port_type,
                speed=speed,
                description=description,
            ),
            dry_run=dry_run,
        ),
        output=output,
        title="Porta de console criada",
    )


@console_ports_app.command("list")
def list_console_ports(
    device: Annotated[str | None, typer.Option("--device")] = None,
    search: Annotated[str | None, typer.Option("--search", "-s")] = None,
    limit: Annotated[int | None, typer.Option(min=0)] = 0,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Lista portas de console."""
    execute(
        lambda: _list_components(
            ConsolePortsService, device=device, search=search, limit=limit
        ),
        output=output,
        title="Portas de console",
    )


@console_ports_app.command("update")
def update_console_port(
    port_id: Annotated[int, typer.Argument(min=1)],
    name: Annotated[str | None, typer.Option("--name", "-n")] = None,
    port_type: Annotated[str | None, typer.Option("--type")] = None,
    speed: Annotated[int | None, typer.Option("--speed", min=1)] = None,
    description: Annotated[str | None, typer.Option("--description")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Atualiza uma porta de console pelo ID."""
    execute(
        lambda: update_resource(
            ConsolePortsService,
            port_id,
            UpdateConsolePort(
                name=name,
                type=port_type,
                speed=speed,
                description=description,
            ),
            dry_run=dry_run,
        ),
        output=output,
        title="Porta de console atualizada",
    )


@console_ports_app.command("delete")
def delete_console_port(
    port_id: Annotated[int, typer.Argument(min=1)],
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    ignore_not_found: Annotated[bool, typer.Option("--ignore-not-found")] = False,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Exclui uma porta de console pelo ID."""
    execute(
        lambda: _delete_component(
            ConsolePortsService,
            port_id,
            resource="console-port",
            dry_run=dry_run,
            ignore_not_found=ignore_not_found,
        ),
        output=output,
        title="Porta de console removida",
    )


@power_ports_app.command("create")
def create_power_port(
    device: Annotated[str, typer.Option("--device")],
    name: Annotated[str, typer.Option("--name", "-n")],
    port_type: Annotated[str | None, typer.Option("--type")] = None,
    maximum_draw: Annotated[int | None, typer.Option("--maximum-draw", min=0)] = None,
    allocated_draw: Annotated[int | None, typer.Option("--allocated-draw", min=0)] = None,
    description: Annotated[str, typer.Option("--description")] = "",
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Cria uma porta de energia."""
    execute(
        lambda: create_resource(
            PowerPortsService,
            AddPowerPort(
                device=device,
                name=name,
                type=port_type,
                maximum_draw=maximum_draw,
                allocated_draw=allocated_draw,
                description=description,
            ),
            dry_run=dry_run,
        ),
        output=output,
        title="Porta de energia criada",
    )


@power_ports_app.command("list")
def list_power_ports(
    device: Annotated[str | None, typer.Option("--device")] = None,
    search: Annotated[str | None, typer.Option("--search", "-s")] = None,
    limit: Annotated[int | None, typer.Option(min=0)] = 0,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Lista portas de energia."""
    execute(
        lambda: _list_components(
            PowerPortsService, device=device, search=search, limit=limit
        ),
        output=output,
        title="Portas de energia",
    )


@power_ports_app.command("update")
def update_power_port(
    port_id: Annotated[int, typer.Argument(min=1)],
    name: Annotated[str | None, typer.Option("--name", "-n")] = None,
    port_type: Annotated[str | None, typer.Option("--type")] = None,
    maximum_draw: Annotated[int | None, typer.Option("--maximum-draw", min=0)] = None,
    allocated_draw: Annotated[int | None, typer.Option("--allocated-draw", min=0)] = None,
    description: Annotated[str | None, typer.Option("--description")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Atualiza uma porta de energia pelo ID."""
    execute(
        lambda: update_resource(
            PowerPortsService,
            port_id,
            UpdatePowerPort(
                name=name,
                type=port_type,
                maximum_draw=maximum_draw,
                allocated_draw=allocated_draw,
                description=description,
            ),
            dry_run=dry_run,
        ),
        output=output,
        title="Porta de energia atualizada",
    )


@power_ports_app.command("delete")
def delete_power_port(
    port_id: Annotated[int, typer.Argument(min=1)],
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    ignore_not_found: Annotated[bool, typer.Option("--ignore-not-found")] = False,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Exclui uma porta de energia pelo ID."""
    execute(
        lambda: _delete_component(
            PowerPortsService,
            port_id,
            resource="power-port",
            dry_run=dry_run,
            ignore_not_found=ignore_not_found,
        ),
        output=output,
        title="Porta de energia removida",
    )


@cables_app.command("create")
def create_cable(
    a_type: Annotated[TerminationType, typer.Option("--a-type")],
    a_device: Annotated[str, typer.Option("--a-device")],
    a_name: Annotated[str, typer.Option("--a-name")],
    b_type: Annotated[TerminationType, typer.Option("--b-type")],
    b_device: Annotated[str, typer.Option("--b-device")],
    b_name: Annotated[str, typer.Option("--b-name")],
    cable_type: Annotated[str | None, typer.Option("--type")] = None,
    status: Annotated[str, typer.Option("--status")] = "connected",
    label: Annotated[str, typer.Option("--label")] = "",
    color: Annotated[str, typer.Option("--color")] = "",
    length: Annotated[float | None, typer.Option("--length", min=0.000001)] = None,
    length_unit: Annotated[str | None, typer.Option("--length-unit")] = None,
    description: Annotated[str, typer.Option("--description")] = "",
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Cria um cabo resolvendo as terminações por dispositivo e nome."""
    execute(
        lambda: create_resource(
            CablesService,
            AddCable(
                a_type=a_type,
                a_device=a_device,
                a_name=a_name,
                b_type=b_type,
                b_device=b_device,
                b_name=b_name,
                type=cable_type,
                status=status,
                label=label,
                color=color,
                length=length,
                length_unit=length_unit,
                description=description,
            ),
            dry_run=dry_run,
        ),
        output=output,
        title="Cabo criado",
    )


@cables_app.command("list")
def list_cables(
    search: Annotated[str | None, typer.Option("--search", "-s")] = None,
    limit: Annotated[int | None, typer.Option(min=0)] = 0,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Lista cabos."""
    execute(
        lambda: make_service(CablesService).list(search=search, limit=limit),
        output=output,
        title="Cabos",
    )


@cables_app.command("update")
def update_cable(
    cable_id: Annotated[int, typer.Argument(min=1)],
    cable_type: Annotated[str | None, typer.Option("--type")] = None,
    status: Annotated[str | None, typer.Option("--status")] = None,
    label: Annotated[str | None, typer.Option("--label")] = None,
    color: Annotated[str | None, typer.Option("--color")] = None,
    length: Annotated[float | None, typer.Option("--length", min=0.000001)] = None,
    length_unit: Annotated[str | None, typer.Option("--length-unit")] = None,
    description: Annotated[str | None, typer.Option("--description")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Atualiza metadados de um cabo pelo ID."""
    execute(
        lambda: update_resource(
            CablesService,
            cable_id,
            UpdateCable(
                type=cable_type,
                status=status,
                label=label,
                color=color,
                length=length,
                length_unit=length_unit,
                description=description,
            ),
            dry_run=dry_run,
        ),
        output=output,
        title="Cabo atualizado",
    )


@cables_app.command("delete")
def delete_cable(
    cable_id: Annotated[int, typer.Argument(min=1)],
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    ignore_not_found: Annotated[bool, typer.Option("--ignore-not-found")] = False,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Exclui um cabo pelo ID."""
    execute(
        lambda: delete_resource(
            CablesService,
            cable_id,
            resource="cable",
            dry_run=dry_run,
            ignore_not_found=ignore_not_found,
        ),
        output=output,
        title="Cabo removido",
    )
