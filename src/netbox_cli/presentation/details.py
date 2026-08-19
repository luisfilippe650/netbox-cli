from __future__ import annotations

import csv
import io
from enum import Enum
from typing import Any

import typer
from rich import box
from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from netbox_cli.presentation.output import console, render_json


class DetailOutputFormat(str, Enum):
    human = "human"
    json = "json"


class InventoryOutputFormat(str, Enum):
    human = "human"
    json = "json"
    csv = "csv"


def render_inspection(data: dict[str, Any], output: DetailOutputFormat) -> None:
    if output is DetailOutputFormat.json:
        render_json(data)
        return

    details = Table.grid(padding=(0, 1))
    details.add_column(style="bold cyan")
    details.add_column()
    for label, field in (
        ("Manufacturer", "manufacturer"),
        ("Device type", "device_type"),
        ("Role", "role"),
        ("Serial", "serial"),
        ("Asset tag", "asset_tag"),
        ("Site", "site"),
        ("Location", "location"),
        ("Rack", "rack"),
        ("Position", "position"),
        ("Face", "face"),
        ("Status", "status"),
        ("Primary IP", "primary_ip"),
        ("Primary IPv4", "primary_ip4"),
        ("Primary IPv6", "primary_ip6"),
        ("OOB IP", "oob_ip"),
        ("Platform", "platform"),
        ("Airflow", "airflow"),
        ("Description", "description"),
        ("Tags", "tags"),
        ("Created", "created"),
        ("Last updated", "last_updated"),
    ):
        value = data.get(field)
        if field == "position" and value is not None:
            value = f"U{_number(value)}"
        if isinstance(value, list):
            value = ", ".join(str(item) for item in value)
        details.add_row(f"{label}:", str(value or "—"))

    interfaces = Tree("[bold]Interfaces[/bold]")
    rows = data.get("interfaces", [])
    if rows:
        for item in rows:
            destination = "não conectado"
            if item.get("connected_device"):
                destination = " ".join(
                    part
                    for part in (
                        str(item["connected_device"]),
                        str(item.get("connected_interface") or ""),
                    )
                    if part
                )
            attributes = [
                str(value)
                for value in (item.get("type"), item.get("mac_address"))
                if value
            ]
            suffix = f" [dim]({' · '.join(attributes)})[/dim]" if attributes else ""
            interfaces.add(
                f"[cyan]{item.get('name') or '—'}[/cyan]{suffix} → {destination}"
            )
    else:
        interfaces.add("[dim]Nenhuma interface[/dim]")

    ip_tree = Tree("[bold]IP Addresses[/bold]")
    ip_rows = data.get("ip_addresses", [])
    if ip_rows:
        for item in ip_rows:
            prefix = f"{item['interface']}: " if item.get("interface") else ""
            ip_tree.add(f"{prefix}{item.get('address') or '—'}")
    else:
        ip_tree.add("[dim]Nenhum endereço IP[/dim]")

    custom_fields = Tree("[bold]Custom Fields[/bold]")
    fields = data.get("custom_fields", {})
    if fields:
        for name, value in sorted(fields.items()):
            custom_fields.add(f"[cyan]{name}[/cyan]: {value if value is not None else '—'}")
    else:
        custom_fields.add("[dim]Nenhum campo personalizado[/dim]")

    components = Tree("[bold]Components[/bold]")
    has_components = False
    for component_type, items in data.get("components", {}).items():
        if not items:
            continue
        has_components = True
        group = components.add(component_type.replace("_", " ").title())
        for item in items:
            group.add(str(item.get("name") or "—"))
    if not has_components:
        components.add("[dim]Nenhum componente adicional[/dim]")

    console.print(
        Panel(
            Group(
                details,
                Text(),
                interfaces,
                Text(),
                ip_tree,
                Text(),
                components,
                Text(),
                custom_fields,
            ),
            title=str(data.get("name") or "Dispositivo"),
            border_style="blue",
        )
    )


def render_search(data: dict[str, Any], output: DetailOutputFormat) -> None:
    if output is DetailOutputFormat.json:
        render_json(data)
        return
    results = data.get("results", [])
    if not results:
        console.print(f"[yellow]Nenhum resultado para '{data.get('query', '')}'.[/yellow]")
        return

    table = Table(title=f"Resultados para {data.get('query')}", box=box.SIMPLE_HEAD)
    table.add_column("TIPO", style="bold cyan")
    table.add_column("NOME", style="bold")
    table.add_column("SITE")
    table.add_column("LOCAL / RACK")
    table.add_column("IP")
    table.add_column("STATUS")
    for item in results:
        location = item.get("rack") or item.get("location") or ""
        table.add_row(
            str(item.get("type", "")).upper(),
            str(item.get("name") or ""),
            str(item.get("site") or ""),
            str(location),
            str(item.get("ip") or item.get("address") or ""),
            str(item.get("status") or ""),
        )
    console.print(table)


def render_rack(data: dict[str, Any], output: DetailOutputFormat) -> None:
    if output is DetailOutputFormat.json:
        render_json(data)
        return

    units_by_number = {
        float(unit["id"]): unit
        for unit in data.get("units", [])
        if isinstance(unit, dict) and _is_number(unit.get("id"))
    }
    integer_units = [
        float(unit["id"])
        for unit in data.get("units", [])
        if isinstance(unit, dict)
        and _is_number(unit.get("id"))
        and float(unit["id"]).is_integer()
    ]
    if not integer_units:
        start = int(data.get("starting_unit") or 1)
        height = int(data.get("u_height") or 0)
        integer_units = [float(number) for number in range(start + height - 1, start - 1, -1)]
    rack = Table(
        title=str(data.get("name") or "Rack"),
        box=box.SQUARE,
        show_header=False,
        padding=(0, 1),
    )
    rack.add_column("U", justify="right", style="bold cyan", no_wrap=True)
    rack.add_column("Equipamento", min_width=28)
    for number in integer_units:
        full_name = _unit_occupant(units_by_number.get(number))
        half_name = _unit_occupant(units_by_number.get(number + 0.5))
        if half_name and half_name != full_name:
            half_name = f"U{_number(number + 0.5)}: {half_name}"
        names = " | ".join(
            name for name in (full_name, half_name) if name
        )
        rack.add_row(f"{int(number):02d}U", names)
    console.print(rack)
    console.print(
        f"[dim]Site: {data.get('site') or '—'}  "
        f"Location: {data.get('location') or '—'}  Face: {data.get('face')}[/dim]"
    )


def render_availability(data: dict[str, Any], output: DetailOutputFormat) -> None:
    if output is DetailOutputFormat.json:
        render_json(data)
        return
    positions = data.get("positions", [])
    if not positions:
        console.print(
            f"[yellow]Não há posição disponível para {data.get('height')}U "
            f"em {data.get('rack')} ({data.get('face')}).[/yellow]"
        )
        return
    formatted = ", ".join(f"U{_number(position)}" for position in positions)
    console.print(
        Panel.fit(
            formatted,
            title=f"{data.get('rack')} · posições disponíveis para {data.get('height')}U",
            border_style="green",
        )
    )


def render_inventory(data: dict[str, Any], output: InventoryOutputFormat) -> None:
    if output is InventoryOutputFormat.json:
        render_json(data)
        return
    rows = data.get("results", [])
    columns = (
        "id",
        "name",
        "role",
        "device_type",
        "site",
        "location",
        "rack",
        "position",
        "status",
        "primary_ip",
        "serial",
    )
    if output is InventoryOutputFormat.csv:
        stream = io.StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        # echo evita ANSI e preserva o CSV para redirecionamento em arquivo.
        typer.echo(stream.getvalue(), nl=False)
        return

    table = Table(title=_inventory_title(data), box=box.SIMPLE_HEAD)
    for column in columns:
        table.add_column(column.upper(), no_wrap=column in {"id", "position"})
    for row in rows:
        table.add_row(*(str(row.get(column) or "") for column in columns))
    console.print(table)


def render_trace(data: dict[str, Any], output: DetailOutputFormat) -> None:
    if output is DetailOutputFormat.json:
        render_json(data)
        return
    root = Tree(
        f"[bold]{data.get('device')}[/bold] [cyan]{data.get('interface')}[/cyan]"
    )
    segments = data.get("segments", [])
    if not segments:
        root.add("[yellow]Sem caminho de cabo registrado[/yellow]")
    else:
        for index, segment in enumerate(segments, start=1):
            cable = segment.get("cable") or {}
            label = cable.get("label") or f"Trecho {index}"
            branch = root.add(f"[bold]Cabo:[/bold] {label}")
            origins = branch.add("[dim]Origem[/dim]")
            for termination in segment.get("near", []):
                origins.add(_termination_label(termination))
            destinations = branch.add("[dim]Destino(s)[/dim]")
            for termination in segment.get("far", []):
                destinations.add(_termination_label(termination))
    console.print(root)


def render_status(data: dict[str, Any], output: DetailOutputFormat) -> None:
    if output is DetailOutputFormat.json:
        render_json(data)
        return
    table = Table.grid(padding=(0, 1))
    table.add_column(style="bold")
    table.add_column()
    table.add_row("URL", str(data.get("url")))
    table.add_row("Alcançável", _yes_no(bool(data.get("reachable"))))
    table.add_row("Token configurado", _yes_no(bool(data.get("token_configured"))))
    table.add_row("Autenticado", _yes_no(bool(data.get("authenticated"))))
    table.add_row("Usuário", str(data.get("user") or "—"))
    if data.get("status_code"):
        table.add_row("HTTP", str(data["status_code"]))
    color = "green" if data.get("authenticated") else "yellow"
    console.print(Panel.fit(table, title="NetBox status", border_style=color))


def render_capacity(data: dict[str, Any], output: DetailOutputFormat) -> None:
    if output is DetailOutputFormat.json:
        render_json(data)
        return
    table = Table.grid(padding=(0, 1))
    table.add_column(style="bold cyan")
    table.add_column(justify="right")
    table.add_row("Site", str(data.get("site") or "—"))
    table.add_row("Location", str(data.get("location") or "—"))
    table.add_row("Total", f"{data.get('total_u')}U")
    table.add_row("Occupied", f"{data.get('occupied_u')}U")
    table.add_row("Free", f"{data.get('free_u')}U")
    table.add_row("Occupancy", f"{data.get('occupancy_percent')}%")
    front = data.get("front", {})
    rear = data.get("rear", {})
    table.add_row("Front free", f"{front.get('free_u')}U")
    table.add_row("Rear free", f"{rear.get('free_u')}U")
    console.print(
        Panel.fit(
            table,
            title=str(data.get("rack") or "Rack capacity"),
            border_style="blue",
        )
    )


def render_site_status(data: dict[str, Any], output: DetailOutputFormat) -> None:
    if output is DetailOutputFormat.json:
        render_json(data)
        return
    site = data.get("site", {})
    capacity = data.get("capacity", {})
    summary = Table.grid(padding=(0, 1))
    summary.add_column(style="bold cyan")
    summary.add_column(justify="right")
    summary.add_row("Status", str(site.get("status") or "—"))
    summary.add_row("Racks", str(data.get("racks", 0)))
    summary.add_row("Devices", str(data.get("devices", 0)))
    summary.add_row("Total U", f"{capacity.get('total_u', 0)}U")
    summary.add_row("Occupied U", f"{capacity.get('occupied_u', 0)}U")
    summary.add_row("Free U", f"{capacity.get('free_u', 0)}U")
    summary.add_row("Occupancy", f"{capacity.get('occupancy_percent', 0)}%")
    manufacturers = Table(box=box.SIMPLE_HEAD)
    manufacturers.add_column("MANUFACTURER")
    manufacturers.add_column("DEVICES", justify="right")
    for item in data.get("manufacturers", []):
        manufacturers.add_row(str(item.get("name")), str(item.get("devices")))
    console.print(
        Panel(
            Group(summary, Text(), manufacturers),
            title=f"Site status · {site.get('name')}",
            border_style="blue",
        )
    )


def render_infrastructure_tree(
    data: dict[str, Any], output: DetailOutputFormat
) -> None:
    if output is DetailOutputFormat.json:
        render_json(data)
        return
    root = Tree("[bold blue]NetBox[/bold blue]")
    for child in data.get("children", []):
        _add_tree_node(root, child)
    console.print(root)


def _is_number(value: object) -> bool:
    try:
        float(str(value))
    except (TypeError, ValueError):
        return False
    return True


def _number(value: object) -> str:
    number = float(str(value))
    return str(int(number)) if number.is_integer() else str(number)


def _unit_occupant(unit: Any) -> str:
    if not isinstance(unit, dict) or not unit.get("occupied"):
        return ""
    device = unit.get("device")
    if isinstance(device, dict):
        return str(device.get("name") or device.get("display") or "")
    return str(unit.get("description") or "Reservado")


def _termination_label(termination: dict[str, Any]) -> str:
    device = f"{termination.get('device')} " if termination.get("device") else ""
    return f"{device}{termination.get('name') or '—'}"


def _inventory_title(data: dict[str, Any]) -> str:
    inventory_filter = data.get("filter", {})
    return f"Inventário · {inventory_filter.get('type')}: {inventory_filter.get('value')}"


def _yes_no(value: bool) -> str:
    return "[green]sim[/green]" if value else "[red]não[/red]"


def _add_tree_node(parent: Tree, node: dict[str, Any]) -> None:
    styles = {
        "region": "bold magenta",
        "site": "bold green",
        "location": "cyan",
        "rack": "yellow",
        "device": "white",
        "group": "dim",
    }
    label = str(node.get("name") or "—")
    if node.get("type") == "device" and node.get("position") is not None:
        label += f" [dim](U{_number(node['position'])})[/dim]"
    branch = parent.add(f"[{styles.get(str(node.get('type')), 'white')}]{label}[/]")
    for child in node.get("children", []):
        _add_tree_node(branch, child)
