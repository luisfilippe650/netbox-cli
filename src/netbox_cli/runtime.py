from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class RuntimeOptions:
    """Opções globais informadas antes do subcomando."""

    url: str | None = None
    token: str | None = None
    timeout: float | None = None
    config_path: Path | None = None
    output: str | None = None


_options = RuntimeOptions()


def configure(options: RuntimeOptions) -> None:
    global _options
    _options = options


def current_options() -> RuntimeOptions:
    return _options


def wants_json() -> bool:
    return _options.output == "json"
