from __future__ import annotations

import typer
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.prompt import Prompt

from netbox_cli.client import NetBoxClient
from netbox_cli.config import ConfigStore, ConfigurationError, Settings
from netbox_cli.exceptions import NetBoxCLIError
from netbox_cli.presentation.errors import show_error
from netbox_cli.presentation.menu import ChoiceMenu, MenuOption
from netbox_cli.service.auth_service import AuthService
from netbox_cli.runtime import client_request_options, current_options

console = Console()
menu = ChoiceMenu(console)


def login() -> None:
    """Autentica no NetBox e salva o token da sessão local."""
    options = current_options()
    store = ConfigStore(options.config_path)

    try:
        store.ensure_exists()
        settings = store.load(url=options.url, timeout=options.timeout)
        login_interactively(store, settings)
    except typer.Exit:
        raise
    except (ConfigurationError, NetBoxCLIError, ValueError) as error:
        show_error(error, console=console)

        raise typer.Exit(code=1) from error
    except (EOFError, KeyboardInterrupt) as error:
        console.print("\n[yellow]Login cancelado.[/yellow]")

        raise typer.Exit(code=1) from error


def login_interactively(
    store: ConfigStore,
    settings: Settings | None = None,
) -> Settings:
    """Solicita credenciais visualmente e persiste somente o token."""
    settings = settings or store.load()
    console.print(
        Panel.fit(
            f"[bold cyan]Login NetBox[/bold cyan]\n{escape(settings.url)}",
            border_style="cyan",
        )
    )

    while True:
        username = Prompt.ask("Usuário").strip()
        password = Prompt.ask("Senha", password=True)
        anonymous_client = NetBoxClient(
            settings.url,
            timeout=settings.timeout,
            **client_request_options(),
        )
        provisioned = None
        authenticated_client = None

        try:
            provisioned = AuthService(anonymous_client).provision(username, password)
            authenticated_client = NetBoxClient(
                settings.url,
                provisioned.value,
                timeout=settings.timeout,
                **client_request_options(),
            )
            authenticated_service = AuthService(authenticated_client)
            authenticated_service.validate()
            authenticated_service.require_superuser()

            previous_token_id = settings.token_id

            if settings.token and previous_token_id is None:
                previous_token_id = authenticated_service.find_token_id(settings.token)

            authenticated_settings = store.save_token(
                provisioned.value,
                token_id=provisioned.id,
                url=settings.url,
                timeout=settings.timeout,
            )

            # O token novo é persistido antes da revogação para que uma falha
            # de escrita local nunca deixe o usuário sem o token anterior.
            if previous_token_id and previous_token_id != provisioned.id:
                try:
                    authenticated_service.revoke(previous_token_id)
                except NetBoxCLIError as error:
                    console.print(
                        "[yellow]O login foi concluído, mas o token anterior "
                        f"não pôde ser revogado: {escape(str(error))}[/yellow]"
                    )
        except (NetBoxCLIError, ConfigurationError) as error:
            if provisioned is not None and authenticated_client is not None:
                try:
                    AuthService(authenticated_client).revoke(provisioned.id)
                except NetBoxCLIError:
                    # A falha original continua sendo a informação útil; uma
                    # eventual falha de limpeza não deve ocultá-la.
                    pass

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
                    "O token foi salvo, a senha não foi armazenada.",
                    border_style="green",
                )
            )

            return authenticated_settings
        finally:
            if authenticated_client is not None:
                authenticated_client.close()

            anonymous_client.close()
