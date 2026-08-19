from __future__ import annotations

from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from netbox_cli.client import NetBoxClientError
from netbox_cli.config import ConfigurationError


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
    else:
        message = str(error)

    content = Text(message or "Ocorreu um erro inesperado.")
    if hint:
        content.append(f"\n\n{hint}", style="yellow")
    target.print(Panel(content, title=title, border_style="red", expand=False))
