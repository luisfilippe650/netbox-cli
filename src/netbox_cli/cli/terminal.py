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
from netbox_cli.schemas.racks import AddRack, AddRackGroup, UpdateRack, UpdateRackGroup
from netbox_cli.service.organization import (
    LocationsService,
    RegionsService,
    SitesService,
)
from netbox_cli.service.racks import RackGroupsService, RacksService

console = Console()


def _optional_id(label: str) -> int | None:
    value = Prompt.ask(label, default="").strip()
    return int(value) if value else None


def _create(resource: str, service: Any) -> None:
    name = Prompt.ask("Nome").strip()

    if resource == "rack-groups":
        item = AddRackGroup(name=name)
    elif resource == "racks":
        item = AddRack(
            site=IntPrompt.ask("ID do site"),
            name=name,
            width=int(
                Prompt.ask("Largura", choices=["10", "19", "21", "23"], default="19")
            ),
            starting_unit=IntPrompt.ask("Unidade inicial", default=1),
            u_height=IntPrompt.ask("Altura U", default=42),
            group=_optional_id("ID do grupo (opcional)"),
            role=_optional_id("ID da função (opcional)"),
            rack_type=_optional_id("ID do tipo (opcional)"),
        )
    elif resource == "regions":
        description = Prompt.ask("Descrição", default="")
        item = AddRegion(name=name, description=description)
    elif resource == "sites":
        description = Prompt.ask("Descrição", default="")
        item = AddSite(
            name=name,
            region=_optional_id("ID da região (opcional)"),
            description=description,
        )
    else:
        description = Prompt.ask("Descrição", default="")
        item = AddLocation(
            name=name,
            site=IntPrompt.ask("ID do site"),
            parent=_optional_id("ID do local pai (opcional)"),
            description=description,
        )

    render_table(service.create(item), title="Criado com sucesso")


def _update_rack_resource(resource: str, service: Any) -> None:
    item_id = IntPrompt.ask("ID")
    if resource == "rack-groups":
        item = UpdateRackGroup(name=Prompt.ask("Novo nome").strip())
    else:
        name = Prompt.ask("Novo nome (opcional)", default="").strip() or None
        item = UpdateRack(
            site=_optional_id("Novo ID do site (opcional)"),
            name=name,
            width=_optional_id("Nova largura (opcional: 10, 19, 21 ou 23)"),
            starting_unit=_optional_id("Nova unidade inicial (opcional)"),
            u_height=_optional_id("Nova altura U (opcional)"),
            group=_optional_id("Novo ID do grupo (opcional)"),
            role=_optional_id("Novo ID da função (opcional)"),
            rack_type=_optional_id("Novo ID do tipo (opcional)"),
        )
    render_table(service.update(item_id, item), title="Atualizado com sucesso")


def _run_action(resource: str, service: Any) -> None:
    is_rack_resource = resource in {"rack-groups", "racks"}
    action = Prompt.ask(
        "Operação",
        choices=(
            ["all", "get", "post", "update", "delete", "back"]
            if is_rack_resource
            else ["list", "view", "post", "delete", "back"]
        ),
        default="all" if is_rack_resource else "list",
    )
    if action == "back":
        return
    if action in {"list", "all"}:
        search = Prompt.ask("Busca (opcional)", default="").strip() or None
        render_table(service.list(search=search), title=resource.capitalize())
    elif action in {"view", "get"}:
        item_id = IntPrompt.ask("ID")
        render_table(service.get(item_id), title=resource.capitalize())
    elif action == "post":
        _create(resource, service)
    elif action == "update":
        _update_rack_resource(resource, service)
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
            "rack-groups": RackGroupsService(client),
            "racks": RacksService(client),
        }
    except ConfigurationError as error:
        console.print(f"[red]Erro de configuração:[/red] {error}")
        raise typer.Exit(code=1) from error

    console.print(
        Panel.fit(
            "[bold cyan]NetBox CLI[/bold cyan]\nOrganização e racks",
            border_style="cyan",
        )
    )
    while True:
        try:
            resource = Prompt.ask(
                "Recurso",
                choices=[
                    "regions",
                    "sites",
                    "locations",
                    "rack-groups",
                    "racks",
                    "quit",
                ],
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
