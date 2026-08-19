from __future__ import annotations

from dataclasses import replace

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import FloatPrompt, Prompt

from netbox_cli.cli.login import login_interactively
from netbox_cli.config import ConfigStore, ConfigurationError, Settings
from netbox_cli.exceptions import NetBoxCLIError
from netbox_cli.presentation.errors import show_error
from netbox_cli.presentation.menu import ChoiceMenu, MenuOption

console = Console()
menu = ChoiceMenu(console)

MAIN_OPTIONS = [
    MenuOption("login", "Login"),
    MenuOption("settings", "Configurações"),
    MenuOption("quit", "Sair"),
]

CONFIG_OPTIONS = [
    MenuOption("url", "Alterar URL"),
    MenuOption("timeout", "Alterar timeout"),
    MenuOption("logout", "Limpar token / sair da conta"),
    MenuOption("back", "Voltar"),
]


def _success(message: str) -> None:
    console.print(Panel.fit(message, border_style="green"))


def _header(settings: Settings, store: ConfigStore) -> None:
    auth_status = (
        "[bold green]Token configurado[/bold green]"
        if settings.token
        else "[bold yellow]Login necessário[/bold yellow]"
    )
    console.print(
        Panel.fit(
            "[bold cyan]NetBox CLI[/bold cyan]\n"
            f"{auth_status}\n"
            f"[dim]{settings.url} • timeout {settings.timeout}s[/dim]\n"
            f"[dim]{store.path}[/dim]",
            border_style="cyan",
        )
    )


def _change_url(store: ConfigStore, settings: Settings) -> None:
    url = Prompt.ask("URL do NetBox", default=settings.url).strip().rstrip("/")
    if not url.startswith(("http://", "https://")):
        raise ConfigurationError("A URL deve começar com http:// ou https://")

    token = settings.token if url == settings.url else ""
    store.save(replace(settings, url=url, token=token))
    message = "URL atualizada."
    if settings.token and not token:
        message += " O token foi limpo; faça login no novo servidor."
    _success(message)


def _change_timeout(store: ConfigStore, settings: Settings) -> None:
    timeout = FloatPrompt.ask("Timeout em segundos", default=settings.timeout)
    if timeout <= 0:
        raise ConfigurationError("O timeout deve ser maior que zero")
    parsed_timeout = float(timeout)
    normalized = int(parsed_timeout) if parsed_timeout.is_integer() else parsed_timeout
    store.save(replace(settings, timeout=normalized))
    _success("Timeout atualizado.")


def _clear_token(store: ConfigStore, settings: Settings) -> None:
    if not settings.token:
        console.print("[yellow]Nenhum token está armazenado.[/yellow]")
        return
    confirmation = menu.ask(
        "Limpar o token armazenado?",
        [MenuOption("yes", "Sim"), MenuOption("no", "Não")],
        selected=1,
    )
    if confirmation == "yes":
        store.save(replace(settings, token=""))
        _success("Token removido. A sessão local foi encerrada.")


def _configuration_menu(store: ConfigStore) -> None:
    while True:
        settings = store.load()
        console.print(
            Panel.fit(
                f"[bold]Configurações[/bold]\n"
                f"URL: [cyan]{settings.url}[/cyan]\n"
                f"Timeout: [cyan]{settings.timeout}s[/cyan]\n"
                f"Token: {'[green]configurado[/green]' if settings.token else '[yellow]vazio[/yellow]'}",
                border_style="blue",
            )
        )
        action = menu.ask("O que deseja configurar?", CONFIG_OPTIONS)
        if action == "back":
            return
        try:
            if action == "url":
                _change_url(store, settings)
            elif action == "timeout":
                _change_timeout(store, settings)
            else:
                _clear_token(store, settings)
        except (ConfigurationError, ValueError) as error:
            show_error(error, console=console)


def run_terminal() -> None:
    """Interface Rich exclusiva para login e configuração."""
    store = ConfigStore()
    try:
        store.ensure_exists()
        while True:
            settings = store.load()
            _header(settings, store)
            action = menu.ask("Escolha uma opção", MAIN_OPTIONS)
            if action == "quit":
                console.print("[cyan]Até logo![/cyan]")
                return
            if action == "settings":
                _configuration_menu(store)
                continue
            try:
                login_interactively(store, settings)
            except typer.Exit:
                continue
    except (ConfigurationError, NetBoxCLIError, ValueError) as error:
        show_error(error, console=console)
        raise typer.Exit(code=1) from error
    except (EOFError, KeyboardInterrupt) as error:
        console.print("\n[cyan]Até logo![/cyan]")
        raise typer.Exit(code=0) from error
