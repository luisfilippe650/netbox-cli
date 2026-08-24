from __future__ import annotations

import json
from enum import Enum
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from netbox_cli.presentation.table_options import TableOptions, select_columns
from netbox_cli.runtime import current_options


class OutputFormat(str, Enum):
    json = "json"
    table = "table"
    id = "id"


console = Console()
error_console = Console(stderr=True)


def is_json_output(output: Enum | str) -> bool:
    """Verifica se a saída efetiva é JSON, respeitando a opção global."""

    global_output = current_options().output

    if global_output is not None:
        return global_output == "json"

    value = output.value if isinstance(output, Enum) else str(output)

    return value == "json"


def _effective_output(output: OutputFormat) -> str:
    global_output = current_options().output

    if global_output == "human":
        return OutputFormat.table.value

    return global_output or output.value


def _display_value(value: Any) -> str:
    """Converte valores simples ou aninhados em texto adequado para tabelas."""

    if value is None:
        return ""

    if isinstance(value, dict):
        for field in ("display", "name", "label", "value", "id"):
            nested = value.get(field)

            if nested is not None and nested != "":
                return str(nested)

        return ""

    if isinstance(value, list):
        return ", ".join(_display_value(item) for item in value)

    return str(value)


def render_json(data: Any) -> None:
    """Serializa e escreve dados como JSON puro, indentado e em UTF-8."""

    # Mantém JSON puro para pipes e scripts, mas com leitura confortável no terminal.
    typer.echo(
        json.dumps(
            data,
            ensure_ascii=False,
            default=str,
            indent=2,
        )
    )


def resource_id(data: Any) -> int | str | None:
    """Extrai o ID de respostas diretas ou de envelopes do ``--ensure``."""
    if not isinstance(data, dict):
        return None

    if data.get("id") is not None:
        return data["id"]

    for field in ("resource", "current"):
        nested = data.get(field)

        if isinstance(nested, dict) and nested.get("id") is not None:
            return nested["id"]

    return None


def render_id(data: Any) -> None:
    """Escreve um ID por linha para respostas únicas ou listagens."""
    rows: list[Any] | None = None

    if isinstance(data, dict) and isinstance(data.get("results"), list):
        rows = data["results"]
    elif isinstance(data, list):
        rows = data

    if rows is not None:
        identifiers = [resource_id(row) for row in rows]

        if any(identifier is None for identifier in identifiers):
            error_console.print(
                "[red]Um ou mais itens da listagem não possuem ID.[/red]"
            )
            raise typer.Exit(code=1)

        for identifier in identifiers:
            typer.echo(identifier)

        return

    identifier = resource_id(data)

    if identifier is None:
        if isinstance(data, dict) and data.get("action") == "would_create":
            message = (
                "A operação não retornou um ID porque o dry-run indica uma criação; "
                "o recurso ainda não existe."
            )
        else:
            message = "A operação não retornou um ID."

        error_console.print(f"[red]{message}[/red]")

        raise typer.Exit(code=1)

    typer.echo(identifier)


def render_table(
    data: Any,
    *,
    title: str,
    table_options: TableOptions | None = None,
) -> None:
    """Exibe dados em uma tabela Rich com as colunas mais relevantes."""

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
        "role",
        "device_type",
        "site",
        "rack",
        "status",
        "location",
        "manufacturer",
        "model",
        "slug",
        "group",
        "rack_type",
        "serial",
        "position",
        "width",
        "starting_unit",
        "u_height",
        "region",
        "parent",
        "description",
    )
    available = [column for column in preferred if any(column in row for row in rows)]

    if not available:
        available = list(rows[0])[:8]

    options = table_options or TableOptions()
    columns = select_columns(
        rows,
        available,
        options,
        terminal_width=console.width,
        display=_display_value,
    )

    table = Table(title=title, show_lines=False)

    for column in columns:
        table.add_column(
            column.upper(),
            no_wrap=column == "id",
            overflow="fold" if options.no_truncate else "ellipsis",
        )

    for row in rows:
        table.add_row(*(_display_value(row.get(column)) for column in columns))

    console.print(table)


def render(
    data: Any,
    output: OutputFormat,
    *,
    title: str,
    table_options: TableOptions | None = None,
) -> None:
    """Encaminha os dados para o renderizador JSON, tabela ou ID."""
    effective_output = _effective_output(output)

    if effective_output == OutputFormat.json.value:
        render_json(data)
    elif effective_output == OutputFormat.id.value:
        render_id(data)
    else:
        render_table(data, title=title, table_options=table_options)
