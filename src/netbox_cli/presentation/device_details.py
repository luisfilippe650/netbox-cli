from __future__ import annotations

from typing import Any

from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from netbox_cli.presentation.formats import DetailOutputFormat
from netbox_cli.presentation.output import console, is_json_output, render_json


def render_inspection(data: dict[str, Any], output: DetailOutputFormat) -> None:
    """Exibe os detalhes, interfaces, IPs e componentes de um dispositivo."""

    if is_json_output(output):
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
    for item in data.get("interfaces", []):
        destination = "não conectado"
        if item.get("connected_device"):
            destination = " ".join(
                str(part)
                for part in (
                    item["connected_device"],
                    item.get("connected_interface") or "",
                )
                if part
            )
        attributes = [
            str(value) for value in (item.get("type"), item.get("mac_address")) if value
        ]
        suffix = f" [dim]({' · '.join(attributes)})[/dim]" if attributes else ""
        interfaces.add(
            f"[cyan]{item.get('name') or '—'}[/cyan]{suffix} → {destination}"
        )
    if not data.get("interfaces"):
        interfaces.add("[dim]Nenhuma interface[/dim]")

    ip_tree = Tree("[bold]IP Addresses[/bold]")
    for item in data.get("ip_addresses", []):
        prefix = f"{item['interface']}: " if item.get("interface") else ""
        ip_tree.add(f"{prefix}{item.get('address') or '—'}")
    if not data.get("ip_addresses"):
        ip_tree.add("[dim]Nenhum endereço IP[/dim]")

    custom_fields = Tree("[bold]Custom Fields[/bold]")
    for name, value in sorted(data.get("custom_fields", {}).items()):
        custom_fields.add(f"[cyan]{name}[/cyan]: {value if value is not None else '—'}")
    if not data.get("custom_fields"):
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


def render_trace(data: dict[str, Any], output: DetailOutputFormat) -> None:
    """Exibe o caminho físico dos cabos conectados a uma interface."""

    if is_json_output(output):
        render_json(data)
        return
    root = Tree(
        f"[bold]{data.get('device')}[/bold] [cyan]{data.get('interface')}[/cyan]"
    )
    segments = data.get("segments", [])
    if not segments:
        root.add("[yellow]Sem caminho de cabo registrado[/yellow]")
    for index, segment in enumerate(segments, start=1):
        cable = segment.get("cable") or {}
        branch = root.add(
            f"[bold]Cabo:[/bold] {cable.get('label') or f'Trecho {index}'}"
        )
        origins = branch.add("[dim]Origem[/dim]")
        for termination in segment.get("near", []):
            origins.add(_termination_label(termination))
        destinations = branch.add("[dim]Destino(s)[/dim]")
        for termination in segment.get("far", []):
            destinations.add(_termination_label(termination))
    console.print(root)


def _number(value: object) -> str:
    """Formata uma posição numérica sem manter casas decimais desnecessárias."""

    number = float(str(value))
    return str(int(number)) if number.is_integer() else str(number)


def _termination_label(termination: dict[str, Any]) -> str:
    """Monta o rótulo de uma terminação usando dispositivo e interface."""

    device = f"{termination.get('device')} " if termination.get("device") else ""
    return f"{device}{termination.get('name') or '—'}"
