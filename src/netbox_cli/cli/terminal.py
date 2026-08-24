from __future__ import annotations

from dataclasses import replace

import typer
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.prompt import FloatPrompt, Prompt

from netbox_cli.cli.login import login_interactively
from netbox_cli.client import NetBoxClient
from netbox_cli.config import ConfigStore, ConfigurationError, Settings
from netbox_cli.exceptions import NetBoxCLIError
from netbox_cli.presentation.errors import show_error
from netbox_cli.presentation.menu import ChoiceMenu, MenuOption
from netbox_cli.service.auth_service import AuthService
from netbox_cli.service.status_service import StatusResult, StatusService
from netbox_cli.runtime import client_request_options, current_options

console = Console()
menu = ChoiceMenu(console)
STATUS_TIMEOUT = 3

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


def _check_status(settings: Settings) -> StatusResult:
    client = NetBoxClient(
        settings.url,
        settings.token,
        timeout=min(float(settings.timeout), STATUS_TIMEOUT),
        **client_request_options(),
    )

    try:
        return StatusService(
            client,
            url=settings.url,
            token_configured=bool(settings.token),
            token_version=settings.token_version,
        ).check()
    finally:
        client.close()


def _header(
    settings: Settings,
    store: ConfigStore,
    status: StatusResult,
) -> None:
    details = status.get("user_details") or {}

    if status.get("authorized"):
        username = escape(str(status.get("user") or "usuário"))
        identity = f"[bold green]Autenticado como {username}[/bold green]"

        if isinstance(details, dict) and details.get("email"):
            identity += f"\n[dim]{escape(str(details['email']))}[/dim]"
    elif status.get("authenticated"):
        identity = "[bold red]Acesso exclusivo para superusuários[/bold red]"
    elif not status.get("reachable"):
        identity = "[bold red]NetBox inacessível[/bold red]"
    elif settings.token:
        identity = "[bold red]Sessão inválida — refaça o login[/bold red]"
    else:
        identity = "[bold yellow]Login necessário[/bold yellow]"

    http_status = status.get("status_code")
    connection = "conectado" if status.get("reachable") else "sem conexão"

    if http_status:
        connection += f" • HTTP {http_status}"

    console.print(
        Panel.fit(
            "[bold cyan]NetBox CLI[/bold cyan]\n"
            f"{identity}\n"
            f"[dim]/api/authentication-check/ • {connection}[/dim]\n"
            f"[dim]{escape(settings.url)} • timeout {settings.timeout}s[/dim]",
            border_style="cyan",
        )
    )


def _change_url(store: ConfigStore, settings: Settings) -> None:
    url = Prompt.ask("URL do NetBox", default=settings.url)
    updated = store.save_url(url)

    if updated.url != settings.url:
        _revoke_stored_token(settings)

    message = "URL atualizada."

    if settings.token and not updated.token:
        message += " O token foi limpo; faça login no novo servidor."

    _success(message)


def _change_timeout(store: ConfigStore, settings: Settings) -> None:
    timeout = FloatPrompt.ask("Timeout em segundos", default=settings.timeout)

    if timeout <= 0:
        raise ConfigurationError("O timeout deve ser maior que zero")

    parsed_timeout = float(timeout)
    normalized = int(parsed_timeout) if parsed_timeout.is_integer() else parsed_timeout
    persisted = store.load(use_environment=False)
    store.save(replace(persisted, timeout=normalized))
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
        _revoke_stored_token(settings)
        store.clear_token()
        _success("Token removido. A sessão local foi encerrada.")


def _revoke_stored_token(settings: Settings) -> None:
    if not settings.token:
        return

    client = NetBoxClient(
        settings.url,
        settings.token,
        timeout=settings.timeout,
        **client_request_options(),
    )

    try:
        service = AuthService(client)
        token_id = settings.token_id or service.find_token_id(settings.token)

        if token_id is not None:
            service.revoke(token_id)
        else:
            console.print(
                "[yellow]Não foi possível identificar o token remoto; "
                "somente a cópia local será removida.[/yellow]"
            )
    except NetBoxCLIError as error:
        console.print(
            "[yellow]O token remoto não pôde ser revogado; "
            f"somente a cópia local será removida: {escape(str(error))}[/yellow]"
        )
    finally:
        client.close()


def _configuration_menu(store: ConfigStore) -> None:
    while True:
        settings = store.load()
        console.print(
            Panel.fit(
                f"[bold]Configurações[/bold]\n"
                f"URL: [cyan]{escape(settings.url)}[/cyan]\n"
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
    options = current_options()
    store = ConfigStore(options.config_path)

    try:
        store.ensure_exists()

        while True:
            settings = store.load(
                url=options.url,
                token=options.token,
                timeout=options.timeout,
            )
            status = _check_status(settings)
            _header(settings, store, status)
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
