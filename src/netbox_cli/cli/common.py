from __future__ import annotations

import json
from collections.abc import Callable, Collection, Mapping
from typing import Any, TypeVar

import typer
from pydantic import ValidationError

from netbox_cli.client.netbox_client import NetBoxClient, NetBoxClientError
from netbox_cli.config import ConfigurationError, ConfigStore, Settings
from netbox_cli.exceptions import NetBoxCLIError
from netbox_cli.presentation.errors import show_error
from netbox_cli.presentation.output import OutputFormat, error_console, render
from netbox_cli.presentation.table_options import TableOptions
from netbox_cli.runtime import client_request_options, current_options

ServiceT = TypeVar("ServiceT")
_open_clients: list[NetBoxClient] = []


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


def explicit_update_fields(
    ctx: typer.Context,
    *,
    required: set[str],
    optional: Mapping[str, str] | Collection[str],
) -> set[str]:
    """Retorna campos obrigatórios e opções realmente presentes na linha de comando."""
    mapping = (
        optional
        if isinstance(optional, Mapping)
        else {parameter: parameter for parameter in optional}
    )

    return required | {
        field
        for parameter, field in mapping.items()
        if _option_is_explicit(ctx, parameter)
    }


def _option_is_explicit(ctx: typer.Context, parameter: str) -> bool:
    source = ctx.get_parameter_source(parameter)

    return source is not None and source.name == "COMMANDLINE"


def make_client() -> NetBoxClient:
    options = current_options()
    settings = ConfigStore(options.config_path).load(
        require_token=True,
        url=options.url,
        token=options.token,
        timeout=options.timeout,
    )
    client = NetBoxClient(
        base_url=settings.netbox_url,
        token=settings.netbox_token,
        timeout=settings.timeout,
        **client_request_options(),
    )
    _open_clients.append(client)

    return client


def config_store() -> ConfigStore:
    return ConfigStore(current_options().config_path)


def load_settings(*, require_token: bool = False) -> Settings:
    options = current_options()

    return config_store().load(
        require_token=require_token,
        url=options.url,
        token=options.token,
        timeout=options.timeout,
    )


def make_service(service_class: type[ServiceT]) -> ServiceT:
    return service_class(make_client())


def create_resource(
    service_class: type[ServiceT],
    item: Any,
    *,
    ensure: bool = False,
    dry_run: bool = False,
    identity_field: str = "name",
    filters: dict[str, Any] | None = None,
    update_fields: set[str] | None = None,
) -> Any:
    service = make_service(service_class)

    if ensure:
        return service.ensure(  # type: ignore[attr-defined]
            item,
            identity_field=identity_field,
            filters=filters,
            update_fields=update_fields,
            dry_run=dry_run,
        )

    payload = service.build_payload(item)  # type: ignore[attr-defined]

    if dry_run:
        return {
            "action": "would_create",
            "changed": True,
            "dry_run": True,
            "payload": payload,
        }

    return service.create(item)  # type: ignore[attr-defined]


def update_resource(
    service_class: type[ServiceT], item_id: int, item: Any, *, dry_run: bool = False
) -> Any:
    service = make_service(service_class)

    if dry_run:
        current = service.get(item_id)  # type: ignore[attr-defined]
        changes = service.changes_for(current, item)  # type: ignore[attr-defined]

        if not changes:
            return {
                "action": "unchanged",
                "changed": False,
                "dry_run": True,
                "id": item_id,
                "resource": current,
            }

        return {
            "action": "would_update",
            "changed": True,
            "dry_run": True,
            "id": item_id,
            "changes": changes,
            "resource": current,
        }

    return service.update(item_id, item)  # type: ignore[attr-defined]


def delete_resource(
    service_class: type[ServiceT],
    item_id: int,
    *,
    resource: str,
    dry_run: bool = False,
    ignore_not_found: bool = False,
) -> dict[str, object]:
    service = make_service(service_class)

    if dry_run:
        try:
            current = service.get(item_id)  # type: ignore[attr-defined]
        except NetBoxClientError as error:
            if not (ignore_not_found and error.status_code == 404):
                raise

            return {
                "action": "unchanged",
                "deleted": False,
                "changed": False,
                "dry_run": True,
                "not_found": True,
                "resource": resource,
                "id": item_id,
            }

        return {
            "action": "would_delete",
            "changed": True,
            "dry_run": True,
            "resource": resource,
            "id": item_id,
            "current": current,
        }

    try:
        service.delete(item_id)  # type: ignore[attr-defined]
    except NetBoxClientError as error:
        if not (ignore_not_found and error.status_code == 404):
            raise

        return {
            "deleted": False,
            "changed": False,
            "not_found": True,
            "resource": resource,
            "id": item_id,
        }

    return {
        "deleted": True,
        "changed": True,
        "resource": resource,
        "id": item_id,
    }


def execute(
    operation: Callable[[], Any],
    *,
    output: OutputFormat,
    title: str,
    table_options: TableOptions | None = None,
) -> None:
    result = _run(operation)
    render(result, output, title=title, table_options=table_options)


def execute_operation(operation: Callable[[], Any]) -> Any:
    """Executa uma operação com o tratamento de erros comum da CLI."""

    return _run(operation)


def _run(operation: Callable[[], Any]) -> Any:
    first_client = len(_open_clients)

    try:
        return operation()
    except (ConfigurationError, NetBoxCLIError, ValidationError) as error:
        show_error(error, console=error_console)

        raise typer.Exit(code=1) from error
    finally:
        clients = _open_clients[first_client:]
        del _open_clients[first_client:]

        for client in clients:
            client.close()
