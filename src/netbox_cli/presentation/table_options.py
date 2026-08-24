from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable

import typer


@dataclass(frozen=True, slots=True)
class TableOptions:
    """Preferências comuns para saídas tabulares."""

    wide: bool = False
    no_truncate: bool = False
    columns: tuple[str, ...] | None = None


def parse_columns(value: str | None) -> tuple[str, ...] | None:
    """Converte uma lista separada por vírgulas, preservando a ordem."""
    if value is None:
        return None

    columns = tuple(
        dict.fromkeys(item.strip() for item in value.split(",") if item.strip())
    )

    if not columns:
        raise typer.BadParameter(
            "informe ao menos uma coluna",
            param_hint="--columns",
        )

    return columns


def select_columns(
    rows: list[dict[str, Any]],
    available: Iterable[str],
    options: TableOptions,
    *,
    terminal_width: int,
    display: Callable[[Any], str] = str,
) -> tuple[str, ...]:
    """Seleciona colunas explícitas, completas ou adequadas ao terminal."""
    available_columns = tuple(available)

    if options.columns is not None:
        unknown = [
            column for column in options.columns if column not in available_columns
        ]

        if unknown:
            valid = ", ".join(available_columns)
            raise typer.BadParameter(
                f"coluna(s) desconhecida(s): {', '.join(unknown)}. "
                f"Disponíveis: {valid}",
                param_hint="--columns",
            )

        return options.columns

    if options.wide or options.no_truncate:
        return available_columns

    selected: list[str] = []
    used_width = 1

    for column in available_columns:
        column_width = _estimated_width(rows, column, display)

        if selected and used_width + column_width > terminal_width:
            continue

        selected.append(column)
        used_width += column_width

    return tuple(selected or available_columns[:1])


def _estimated_width(
    rows: list[dict[str, Any]],
    column: str,
    display: Callable[[Any], str],
) -> int:
    content_width = max(
        [len(column), *(len(display(row.get(column))) for row in rows)],
    )

    # Uma célula muito longa não deve expulsar todas as demais colunas.
    return min(max(content_width, 4), 24) + 3
