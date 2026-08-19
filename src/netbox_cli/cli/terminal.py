from __future__ import annotations

from typing import Any

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt

from netbox_cli.cli.common import make_client
from netbox_cli.config import ConfigurationError
from netbox_cli.exceptions import NetBoxCLIError
from netbox_cli.presentation.output import render_table
from netbox_cli.schemas.organization import AddLocation, AddRegion, AddSite
from netbox_cli.service.organization import LocationsService, RegionsService, SitesService

console = Console()


def _optional_id(label: str) -> int | None:
    value = Prompt.ask(label, default="").strip()
    return int(value) if value else None


def _create(resource: str, service: Any) -> None:
    name = Prompt.ask("Nome").strip()
    description = Prompt.ask("Descrição", default="")

    if resource == "regions":
        item = AddRegion(name=name, description=description)
    elif resource == "sites":
        item = AddSite(
            name=name,
            region=_optional_id("ID da região (opcional)"),
            description=description,
        )
    else:
        item = AddLocation(
            name=name,
            site=IntPrompt.ask("ID do site"),
            parent=_optional_id("ID do local pai (opcional)"),
            description=description,
        )

    render_table(service.create(item), title="Criado com sucesso")


def _run_action(resource: str, service: Any) -> None:
    action = Prompt.ask(
        "Operação",
        choices=["list", "view", "post", "delete", "back"],
        default="list",
    )
    if action == "back":
        return
    if action == "list":
        search = Prompt.ask("Busca (opcional)", default="").strip() or None
        render_table(service.list(search=search), title=resource.capitalize())
    elif action == "view":
        item_id = IntPrompt.ask("ID")
        render_table(service.get(item_id), title=resource.capitalize())
    elif action == "post":
        _create(resource, service)
    else:
        item_id = IntPrompt.ask("ID")
        if Confirm.ask(f"Excluir o item {item_id}?", default=False):
            service.delete(item_id)
            console.print("[green]Item excluído com sucesso.[/green]")


def run_terminal() -> None:
    """Executa o menu Rich que reutiliza os mesmos serviços do CLI direto."""
    try:
        client = make_client()
        services = {
            "regions": RegionsService(client),
            "sites": SitesService(client),
            "locations": LocationsService(client),
        }
    except ConfigurationError as error:
        console.print(f"[red]Erro de configuração:[/red] {error}")
        raise typer.Exit(code=1) from error

    console.print(
        Panel.fit(
            "[bold cyan]NetBox CLI[/bold cyan]\nRegiões, sites e locais",
            border_style="cyan",
        )
    )
    while True:
        try:
            resource = Prompt.ask(
                "Recurso",
                choices=["regions", "sites", "locations", "quit"],
                default="regions",
            )
            if resource == "quit":
                break
            _run_action(resource, services[resource])
        except (NetBoxCLIError, ValidationError, ValueError) as error:
            console.print(f"[red]Erro:[/red] {error}")
        except (EOFError, KeyboardInterrupt):
            console.print("\nAté logo!")
            break
    client.close()
