from __future__ import annotations

import json

from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from netbox_cli.client import NetBoxClientError
from netbox_cli.config import ConfigurationError
from netbox_cli.exceptions import NetBoxCLIError
from netbox_cli.runtime import wants_json


def _validation_message(error: ValidationError) -> str:
    lines = []
    for item in error.errors(include_url=False):
        field = ".".join(str(part) for part in item["loc"]) or "dados"
        lines.append(f"• {field}: {item['msg']}")
    return "\n".join(lines)


def show_error(error: Exception, *, console: Console | None = None) -> None:
    target = console or Console(stderr=True)
    title = "Erro"
    hint: str | None = None

    if isinstance(error, ValidationError):
        title = "Dados inválidos"
        message = _validation_message(error)
        hint = "Revise os campos informados e tente novamente."
    elif isinstance(error, ConfigurationError):
        title = "Configuração inválida"
        message = str(error)
        hint = "Abra 'netbox' para revisar login e configuração."
    elif isinstance(error, NetBoxClientError):
        title = "Falha na comunicação"
        message = str(error)
        if error.status_code in {401, 403}:
            title = "Acesso negado"
            hint = "Abra 'netbox' e faça login novamente."
        elif error.status_code == 404:
            hint = "Confira se o recurso ou ID informado existe."
    elif isinstance(error, NetBoxCLIError):
        title = "Operação não concluída"
        message = str(error)
        hint = "Revise os dados informados e tente novamente."
    else:
        message = str(error)

    if wants_json():
        code = {
            "ResourceNotFoundError": "resource_not_found",
            "AmbiguousResourceError": "ambiguous_resource",
            "AuthenticationError": "authentication_error",
            "SuperuserRequiredError": "superuser_required",
            "InputError": "input_error",
            "InventoryFilterError": "invalid_filter",
            "PaginationError": "pagination_error",
        }.get(type(error).__name__, "operation_failed")
        status = getattr(error, "status_code", None)
        if isinstance(error, ValidationError):
            code = "validation_error"
        elif isinstance(error, ConfigurationError):
            code = "configuration_error"
        elif isinstance(error, NetBoxClientError):
            code = "http_error" if status is not None else "connection_error"
        serialized = json.dumps(
            {
                "error": {
                    "code": code,
                    "message": message,
                    **({"status": status} if status is not None else {}),
                }
            },
            ensure_ascii=False,
        )
        target.file.write(f"{serialized}\n")
        target.file.flush()
        return

    content = Text(message or "Ocorreu um erro inesperado.")
    if hint:
        content.append(f"\n\n{hint}", style="yellow")
    target.print(Panel(content, title=title, border_style="red", expand=False))
