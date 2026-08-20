from __future__ import annotations

from typing import Any

from rich import box
from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from netbox_cli.presentation.formats import DetailOutputFormat
from netbox_cli.presentation.output import console, render_json


def render_search(data: dict[str, Any], output: DetailOutputFormat) -> None:
    if output is DetailOutputFormat.json:
        render_json(data)
        return
    results = data.get("results", [])
    if not results:
        console.print(
            f"[yellow]Nenhum resultado para '{data.get('query', '')}'.[/yellow]"
        )
        return
    table = Table(title=f"Resultados para {data.get('query')}", box=box.SIMPLE_HEAD)
    for label, style in (
        ("TIPO", "bold cyan"),
        ("NOME", "bold"),
        ("SITE", None),
        ("LOCAL / RACK", None),
        ("IP", None),
        ("STATUS", None),
    ):
        table.add_column(label, style=style)
    for item in results:
        table.add_row(
            str(item.get("type", "")).upper(),
            str(item.get("name") or ""),
            str(item.get("site") or ""),
            str(item.get("rack") or item.get("location") or ""),
            str(item.get("ip") or item.get("address") or ""),
            str(item.get("status") or ""),
        )
    console.print(table)


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


def render_site_status(data: dict[str, Any], output: DetailOutputFormat) -> None:
    if output is DetailOutputFormat.json:
        render_json(data)
        return
    site = data.get("site", {})
    capacity = data.get("capacity", {})
    summary = Table.grid(padding=(0, 1))
    summary.add_column(style="bold cyan")
    summary.add_column(justify="right")
    for label, value in (
        ("Status", site.get("status") or "—"),
        ("Racks", data.get("racks", 0)),
        ("Devices", data.get("devices", 0)),
        ("Total U", f"{capacity.get('total_u', 0)}U"),
        ("Occupied U", f"{capacity.get('occupied_u', 0)}U"),
        ("Free U", f"{capacity.get('free_u', 0)}U"),
        ("Occupancy", f"{capacity.get('occupancy_percent', 0)}%"),
    ):
        summary.add_row(label, str(value))
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


def _yes_no(value: bool) -> str:
    return "[green]sim[/green]" if value else "[red]não[/red]"


def _number(value: object) -> str:
    number = float(str(value))
    return str(int(number)) if number.is_integer() else str(number)


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
