from typing import Annotated

import typer

from netbox_cli.cli.common import execute_operation, make_service
from netbox_cli.client import NetBoxClient
from netbox_cli.config import ConfigStore
from netbox_cli.presentation.details import (
    DetailOutputFormat,
    InventoryOutputFormat,
    render_inventory,
    render_inspection,
    render_search,
    render_status,
    render_trace,
    render_infrastructure_tree,
)
from netbox_cli.service.devices import DevicesService
from netbox_cli.service.inventory_service import InventoryService
from netbox_cli.service.infrastructure_service import InfrastructureService
from netbox_cli.service.search_service import SearchService
from netbox_cli.service.status_service import StatusService


def inspect_device(
    name: Annotated[str, typer.Argument(help="Nome exato do dispositivo.")],
    site: Annotated[str | None, typer.Option("--site")] = None,
    output: Annotated[
        DetailOutputFormat, typer.Option("--output", "-o")
    ] = DetailOutputFormat.human,
) -> None:
    """Exibe localização, conexões e endereços IP de um dispositivo."""
    result = execute_operation(
        lambda: make_service(DevicesService).inspect(name, site_name=site)
    )
    render_inspection(result, output)


def search(
    query: Annotated[str, typer.Argument(help="Texto a procurar no NetBox.")],
    limit: Annotated[
        int, typer.Option("--limit", min=1, help="Limite por tipo de recurso.")
    ] = 10,
    output: Annotated[
        DetailOutputFormat, typer.Option("--output", "-o")
    ] = DetailOutputFormat.human,
) -> None:
    """Faz uma busca geral por dispositivos, racks, sites, locais e IPs."""
    result = execute_operation(
        lambda: make_service(SearchService).search(query, limit=limit)
    )
    render_search(result, output)


def inventory(
    site: Annotated[str | None, typer.Option("--site")] = None,
    rack: Annotated[str | None, typer.Option("--rack")] = None,
    location: Annotated[str | None, typer.Option("--location")] = None,
    output: Annotated[
        InventoryOutputFormat, typer.Option("--output", "-o")
    ] = InventoryOutputFormat.human,
) -> None:
    """Lista o inventário de dispositivos de um site ou rack."""
    result = execute_operation(
        lambda: make_service(InventoryService).inventory(
            site_name=site,
            rack_name=rack,
            location_name=location,
        )
    )
    render_inventory(result, output)


def trace(
    device: Annotated[str, typer.Argument(help="Nome exato do dispositivo.")],
    interface: Annotated[str, typer.Argument(help="Nome exato da interface.")],
    site: Annotated[str | None, typer.Option("--site")] = None,
    output: Annotated[
        DetailOutputFormat, typer.Option("--output", "-o")
    ] = DetailOutputFormat.human,
) -> None:
    """Rastreia o caminho físico de uma interface através dos cabos."""
    result = execute_operation(
        lambda: make_service(DevicesService).trace(device, interface, site_name=site)
    )
    render_trace(result, output)


def status(
    output: Annotated[
        DetailOutputFormat, typer.Option("--output", "-o")
    ] = DetailOutputFormat.human,
) -> None:
    """Verifica a URL configurada e o estado da autenticação."""
    settings = execute_operation(lambda: ConfigStore().load())
    client = NetBoxClient(
        settings.netbox_url,
        settings.netbox_token,
        timeout=settings.timeout,
    )
    try:
        result = StatusService(
            client,
            url=settings.netbox_url,
            token_configured=bool(settings.netbox_token),
        ).check()
    finally:
        client.close()
    render_status(result, output)
    if not result["authenticated"]:
        raise typer.Exit(code=1)


def tree(
    site: Annotated[str | None, typer.Option("--site")] = None,
    output: Annotated[
        DetailOutputFormat, typer.Option("--output", "-o")
    ] = DetailOutputFormat.human,
) -> None:
    """Exibe região, site, local, rack e dispositivo como uma hierarquia."""
    result = execute_operation(
        lambda: make_service(InfrastructureService).tree(site_name=site)
    )
    render_infrastructure_tree(result, output)
