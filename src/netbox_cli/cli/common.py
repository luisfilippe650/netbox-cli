from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

import typer
from pydantic import ValidationError

from netbox_cli.client.netbox_client import NetBoxClient
from netbox_cli.config import ConfigurationError, Settings
from netbox_cli.exceptions import NetBoxCLIError
from netbox_cli.presentation.output import OutputFormat, error_console, render

ServiceT = TypeVar("ServiceT")


def make_client() -> NetBoxClient:
    settings = Settings.from_env()
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
        error_console.print(f"[red]Erro:[/red] {error}")
        raise typer.Exit(code=1) from error
    render(result, output, title=title)
