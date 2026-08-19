from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, TypeVar

import typer
from pydantic import ValidationError

from netbox_cli.client.netbox_client import NetBoxClient
from netbox_cli.config import ConfigurationError, ConfigStore
from netbox_cli.exceptions import NetBoxCLIError
from netbox_cli.presentation.errors import show_error
from netbox_cli.presentation.output import OutputFormat, error_console, render

ServiceT = TypeVar("ServiceT")


class InputError(NetBoxCLIError):
    """Entrada de linha de comando inválida."""


def parse_json_object(value: str, *, option_name: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as error:
        raise InputError(
            f"{option_name} deve conter JSON válido: {error.msg}"
        ) from error
    if not isinstance(parsed, dict):
        raise InputError(f"{option_name} deve ser um objeto JSON")
    return parsed


def make_client() -> NetBoxClient:
    settings = ConfigStore().load(require_token=True)
    return NetBoxClient(
        base_url=settings.netbox_url,
        token=settings.netbox_token,
        timeout=settings.timeout,
    )


def make_service(service_class: type[ServiceT]) -> ServiceT:
    return service_class(make_client())


def execute(
    operation: Callable[[], Any],
    *,
    output: OutputFormat,
    title: str,
) -> None:
    try:
        result = operation()
    except (ConfigurationError, NetBoxCLIError, ValidationError) as error:
        show_error(error, console=error_console)
        raise typer.Exit(code=1) from error
    render(result, output, title=title)
