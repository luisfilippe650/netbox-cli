from __future__ import annotations

import json
from enum import Enum
from typing import Any

import typer
from rich.console import Console
from rich.table import Table


class OutputFormat(str, Enum):
    json = "json"
    table = "table"


console = Console()
error_console = Console(stderr=True)


def _display_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        return str(value.get("display") or value.get("name") or value.get("id") or "")
    if isinstance(value, list):
        return ", ".join(_display_value(item) for item in value)
    return str(value)


def render_json(data: Any) -> None:
    # typer.echo mantém a saída livre de ANSI para pipes, agentes e scripts.
    typer.echo(json.dumps(data, ensure_ascii=False, default=str))


def render_table(data: Any, *, title: str) -> None:
    rows = (
        data.get("results", [])
        if isinstance(data, dict) and "results" in data
        else [data]
    )
    rows = [row for row in rows if isinstance(row, dict)]

    if not rows:
        console.print(f"[yellow]Nenhum {title.lower()} encontrado.[/yellow]")
        return

    preferred = (
        "id",
        "name",
        "slug",
        "status",
        "site",
        "group",
        "role",
        "rack_type",
        "width",
        "starting_unit",
        "u_height",
        "region",
        "parent",
        "description",
    )
    columns = [column for column in preferred if any(column in row for row in rows)]
    if not columns:
        columns = list(rows[0])[:8]

    table = Table(title=title, show_lines=False)
    for column in columns:
        table.add_column(column.upper(), no_wrap=column == "id")
    for row in rows:
        table.add_row(*(_display_value(row.get(column)) for column in columns))
    console.print(table)


def render(data: Any, output: OutputFormat, *, title: str) -> None:
    if output is OutputFormat.json:
        render_json(data)
    else:
        render_table(data, title=title)
