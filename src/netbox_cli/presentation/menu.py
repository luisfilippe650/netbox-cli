from __future__ import annotations

import sys
import termios
import tty
from dataclasses import dataclass

from rich.console import Console
from rich.live import Live
from rich.text import Text


@dataclass(frozen=True, slots=True)
class MenuOption:
    value: str
    label: str


class ChoiceMenu:
    """Menu Rich navegável por teclado, com fallback para entrada numerada."""

    def __init__(self, console: Console | None = None) -> None:
        """Inicializa o menu com o console informado ou com um novo console."""

        self.console = console or Console()

    def ask(
        self,
        title: str,
        options: list[MenuOption],
        *,
        selected: int = 0,
    ) -> str:
        """Solicita uma escolha usando navegação interativa ou entrada numerada."""

        if not options:
            raise ValueError("O menu precisa ter ao menos uma opção")
        selected = max(0, min(selected, len(options) - 1))

        if not sys.stdin.isatty():
            return self._ask_numbered(title, options, selected)
        return self._ask_interactive(title, options, selected)

    def _ask_interactive(
        self,
        title: str,
        options: list[MenuOption],
        selected: int,
    ) -> str:
        """Captura as teclas de navegação e devolve o valor selecionado."""

        file_descriptor = sys.stdin.fileno()
        previous_settings = termios.tcgetattr(file_descriptor)
        try:
            # cbreak captura as teclas imediatamente sem desativar o tratamento
            # de quebras de linha usado pelo Rich na saída do terminal.
            tty.setcbreak(file_descriptor)
            with Live(
                self._render(title, options, selected),
                console=self.console,
                auto_refresh=False,
                transient=True,
            ) as live:
                while True:
                    key = sys.stdin.read(1)
                    if key == "\x03":
                        raise KeyboardInterrupt
                    if key in {"\r", "\n"}:
                        break
                    if key == "\x1b":
                        sequence = sys.stdin.read(2)
                        if sequence == "[A":
                            selected = (selected - 1) % len(options)
                        elif sequence == "[B":
                            selected = (selected + 1) % len(options)
                    elif key in {"k", "K"}:
                        selected = (selected - 1) % len(options)
                    elif key in {"j", "J"}:
                        selected = (selected + 1) % len(options)
                    live.update(self._render(title, options, selected), refresh=True)
        finally:
            termios.tcsetattr(file_descriptor, termios.TCSADRAIN, previous_settings)

        choice = options[selected]
        self.console.print(f"[dim]{title}:[/dim] [cyan]{choice.label}[/cyan]")
        return choice.value

    def _ask_numbered(
        self,
        title: str,
        options: list[MenuOption],
        selected: int,
    ) -> str:
        """Solicita o número de uma opção quando não há terminal interativo."""

        self.console.print(f"[bold]{title}[/bold]")
        for index, option in enumerate(options, start=1):
            self.console.print(f"  [cyan]{index}[/cyan]. {option.label}")
        while True:
            value = input(f"Escolha [{selected + 1}]: ").strip()
            if not value:
                return options[selected].value
            if value.isdigit() and 1 <= int(value) <= len(options):
                return options[int(value) - 1].value
            self.console.print("[red]Escolha uma opção válida.[/red]")

    @staticmethod
    def _render(title: str, options: list[MenuOption], selected: int) -> Text:
        """Constrói o conteúdo Rich do menu destacando a opção atual."""

        menu = Text(title, style="bold")
        menu.append("\n\n")
        for index, option in enumerate(options):
            if index == selected:
                menu.append("❯ ", style="bold cyan")
                menu.append(option.label, style="bold reverse cyan")
            else:
                menu.append("  ")
                menu.append(option.label)
            menu.append("\n")
        menu.append("\n↑/↓ navegar  •  Enter selecionar", style="dim")
        return menu
