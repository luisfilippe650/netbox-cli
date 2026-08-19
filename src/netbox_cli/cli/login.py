from __future__ import annotations

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from netbox_cli.client import NetBoxClient
from netbox_cli.config import ConfigStore, ConfigurationError, Settings
from netbox_cli.exceptions import NetBoxCLIError
from netbox_cli.presentation.errors import show_error
from netbox_cli.presentation.menu import ChoiceMenu, MenuOption
from netbox_cli.service.auth_service import AuthService

console = Console()
menu = ChoiceMenu(console)


def login_interactively(
    store: ConfigStore,
    settings: Settings | None = None,
) -> Settings:
    """Solicita credenciais visualmente e persiste somente o token."""
    settings = settings or store.load()
    console.print(
        Panel.fit(
            f"[bold cyan]Login NetBox[/bold cyan]\n{settings.url}",
            border_style="cyan",
        )
    )

    while True:
        username = Prompt.ask("Usuário").strip()
        password = Prompt.ask("Senha", password=True)
        anonymous_client = NetBoxClient(settings.url, timeout=settings.timeout)
        try:
            token = AuthService(anonymous_client).login(username, password)
            authenticated_settings = store.save_token(token)
        except (NetBoxCLIError, ConfigurationError) as error:
            show_error(error, console=console)
            retry = menu.ask(
                "Tentar novamente?",
                [MenuOption("yes", "Sim"), MenuOption("no", "Não")],
            )
            if retry == "no":
                raise typer.Exit(code=1) from error
        else:
            console.print(
                Panel.fit(
                    "[bold green]Login realizado com sucesso[/bold green]\n"
                    "O token foi salvo; a senha não foi armazenada.",
                    border_style="green",
                )
            )
            return authenticated_settings
        finally:
            anonymous_client.close()
