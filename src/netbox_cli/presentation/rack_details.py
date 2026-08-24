from __future__ import annotations

from typing import Any

from rich import box
from rich.panel import Panel
from rich.table import Table

from netbox_cli.presentation.formats import DetailOutputFormat
from netbox_cli.presentation.output import console, is_json_output, render_json


def render_rack(data: dict[str, Any], output: DetailOutputFormat) -> None:
    """Exibe a elevação de um rack com os equipamentos em cada unidade."""

    if is_json_output(output):
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
        integer_units = [
            float(number) for number in range(start + height - 1, start - 1, -1)
        ]

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

        rack.add_row(
            f"{int(number):02d}U",
            " | ".join(name for name in (full_name, half_name) if name),
        )

    console.print(rack)
    console.print(
        f"[dim]Site: {data.get('site') or '—'}  "
        f"Location: {data.get('location') or '—'}  Face: {data.get('face')}[/dim]"
    )


def render_availability(data: dict[str, Any], output: DetailOutputFormat) -> None:
    """Exibe as posições capazes de acomodar um dispositivo no rack."""

    if is_json_output(output):
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


def render_capacity(data: dict[str, Any], output: DetailOutputFormat) -> None:
    """Exibe o resumo de capacidade e ocupação de um rack."""

    if is_json_output(output):
        render_json(data)

        return

    table = Table.grid(padding=(0, 1))
    table.add_column(style="bold cyan")
    table.add_column(justify="right")

    for label, value in (
        ("Site", data.get("site") or "—"),
        ("Location", data.get("location") or "—"),
        ("Total", f"{data.get('total_u')}U"),
        ("Occupied", f"{data.get('occupied_u')}U"),
        ("Free", f"{data.get('free_u')}U"),
        ("Occupancy", f"{data.get('occupancy_percent')}%"),
        ("Front free", f"{data.get('front', {}).get('free_u')}U"),
        ("Rear free", f"{data.get('rear', {}).get('free_u')}U"),
    ):
        table.add_row(label, str(value))

    console.print(
        Panel.fit(
            table, title=str(data.get("rack") or "Rack capacity"), border_style="blue"
        )
    )


def _is_number(value: object) -> bool:
    """Indica se um valor pode ser interpretado como número."""

    try:
        float(str(value))
    except (TypeError, ValueError):
        return False

    return True


def _number(value: object) -> str:
    """Formata uma unidade de rack sem casas decimais desnecessárias."""

    number = float(str(value))

    return str(int(number)) if number.is_integer() else str(number)


def _unit_occupant(unit: Any) -> str:
    """Obtém o nome do dispositivo ou da reserva que ocupa uma unidade."""

    if not isinstance(unit, dict) or not unit.get("occupied"):
        return ""

    device = unit.get("device")

    if isinstance(device, dict):
        return str(device.get("name") or device.get("display") or "")

    return str(unit.get("description") or "Reservado")
