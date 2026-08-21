from __future__ import annotations

from typing import Any

from rich import box
from rich.console import Group
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from netbox_cli.presentation.formats import DetailOutputFormat
from netbox_cli.presentation.output import console, is_json_output, render_json


def render_search(data: dict[str, Any], output: DetailOutputFormat) -> None:
    """Exibe resultados de busca com localização, IP e status dos recursos."""

    if is_json_output(output):
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
    """Exibe conectividade, autenticação e dados do usuário do NetBox."""

    if is_json_output(output):
        render_json(data)
        return
    table = Table.grid(padding=(0, 1))
    table.add_column(style="bold")
    table.add_column()
    table.add_row("URL", Text(str(data.get("url"))))
    table.add_row("Verificação", Text(str(data.get("endpoint") or "—")))
    table.add_row("Alcançável", _yes_no(bool(data.get("reachable"))))
    table.add_row("Token configurado", _yes_no(bool(data.get("token_configured"))))
    token_version = data.get("token_version")
    table.add_row("Versão do token", f"v{token_version}" if token_version else "—")
    table.add_row("Autenticado", _yes_no(bool(data.get("authenticated"))))
    table.add_row("Superusuário", _yes_no(bool(data.get("superuser"))))
    table.add_row("Uso autorizado", _yes_no(bool(data.get("authorized"))))
    details = data.get("user_details") or {}
    table.add_row(
        "Usuário",
        Text(str(details.get("username") or data.get("user") or "—")),
    )
    table.add_row(
        "Nome",
        Text(str(details.get("full_name") or details.get("display") or "—")),
    )
    table.add_row("E-mail", Text(str(details.get("email") or "—")))
    if details.get("active") is not None:
        table.add_row("Usuário ativo", _yes_no(bool(details.get("active"))))
    groups = details.get("groups") or []
    table.add_row(
        "Grupos",
        Text(", ".join(str(group) for group in groups) or "—"),
    )
    if details:
        table.add_row("Último login", Text(str(details.get("last_login") or "—")))
    if data.get("status_code"):
        table.add_row("HTTP", str(data["status_code"]))
    if data.get("message"):
        table.add_row(
            "Diagnóstico",
            Text(str(data["message"]).replace("\n", " · ")),
        )
    color = "green" if data.get("authorized") else "yellow"
    console.print(Panel.fit(table, title="NetBox status", border_style=color))


def render_site_status(data: dict[str, Any], output: DetailOutputFormat) -> None:
    """Exibe capacidade e distribuição de dispositivos de um site."""

    if is_json_output(output):
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
    """Exibe regiões, sites, racks e dispositivos como árvore hierárquica."""

    if is_json_output(output):
        render_json(data)
        return
    root = Tree(_tree_label(data, root=True))
    for child in data.get("children", []):
        _add_tree_node(root, child)
    console.print(root)


def _yes_no(value: bool) -> str:
    """Representa um booleano como sim ou não com cores Rich."""

    return "[green]sim[/green]" if value else "[red]não[/red]"


def _number(value: object) -> str:
    """Formata posições numéricas sem casas decimais desnecessárias."""

    number = float(str(value))
    return str(int(number)) if number.is_integer() else str(number)


def _add_tree_node(parent: Tree, node: dict[str, Any]) -> None:
    """Adiciona recursivamente um nó e seus descendentes à árvore Rich."""

    styles = {
        "region": "bold magenta",
        "site": "bold green",
        "location": "cyan",
        "rack": "yellow",
        "device": "white",
        "interface": "bold cyan",
        "connection": "green",
        "ip": "magenta",
        "component": "blue",
        "group": "dim",
    }
    node_type = str(node.get("type"))
    label = _tree_label(node)
    branch = parent.add(f"[{styles.get(node_type, 'white')}]{label}[/]")
    for child in node.get("children", []):
        _add_tree_node(branch, child)


def _tree_label(node: dict[str, Any], *, root: bool = False) -> str:
    """Monta o rótulo Rich de um nó conforme seu tipo e seus atributos."""

    node_type = str(node.get("type") or "root")
    label = escape(str(node.get("name") or "NetBox"))
    if node_type == "connection":
        label = f"→ {label}"
    elif node_type == "ip":
        label = f"IP {label}"
    if node_type in {"device", "rack"} and node.get("position") is not None:
        label += f" [dim](U{_number(node['position'])})[/dim]"
    if node_type == "interface" and node.get("enabled") is False:
        label += " [dim](desabilitada)[/dim]"
    if root:
        style = {
            "rack": "bold yellow",
            "device": "bold white",
        }.get(node_type, "bold blue")
        return f"[{style}]{label}[/]"
    return label
