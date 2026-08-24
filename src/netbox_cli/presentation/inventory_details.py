from __future__ import annotations

import csv
import io
from typing import Any

import typer
from rich import box
from rich.table import Table

from netbox_cli.presentation.formats import InventoryOutputFormat
from netbox_cli.presentation.output import console, is_json_output, render_json
from netbox_cli.presentation.table_options import TableOptions, select_columns


INVENTORY_COLUMNS = (
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


def render_inventory(
    data: dict[str, Any],
    output: InventoryOutputFormat,
    *,
    table_options: TableOptions | None = None,
) -> None:
    """Exibe um inventário de dispositivos em formato humano, JSON ou CSV."""

    if is_json_output(output):
        render_json(data)

        return

    rows = data.get("results", [])
    options = table_options or TableOptions()
    selection_options = (
        TableOptions(wide=True, columns=options.columns)
        if output is InventoryOutputFormat.csv
        else options
    )
    columns = select_columns(
        rows,
        INVENTORY_COLUMNS,
        selection_options,
        terminal_width=console.width,
        display=lambda value: str(value or ""),
    )

    if output is InventoryOutputFormat.csv:
        stream = io.StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        typer.echo(stream.getvalue(), nl=False)

        return

    table = Table(title=_inventory_title(data), box=box.SIMPLE_HEAD)

    for column in columns:
        table.add_column(
            column.upper(),
            no_wrap=column in {"id", "position"},
            overflow="fold" if options.no_truncate else "ellipsis",
        )

    for row in rows:
        table.add_row(*(str(row.get(column) or "") for column in columns))

    console.print(table)


def _inventory_title(data: dict[str, Any]) -> str:
    """Monta o título da tabela a partir do filtro aplicado ao inventário."""

    inventory_filter = data.get("filter", {})

    return (
        f"Inventário · {inventory_filter.get('type')}: {inventory_filter.get('value')}"
    )
