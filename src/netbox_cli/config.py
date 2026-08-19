from __future__ import annotations

import os
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

import yaml


DEFAULT_URL = "http://localhost:8000"
DEFAULT_TIMEOUT = 15


class ConfigurationError(ValueError):
    """Configuração obrigatória ausente ou inválida."""


def default_config_path() -> Path:
    config_root = Path(
        os.getenv("XDG_CONFIG_HOME", str(Path.home() / ".config"))
    ).expanduser()
    return config_root / "netbox-cli" / "config.yaml"


@dataclass(frozen=True, slots=True)
class Settings:
    url: str = DEFAULT_URL
    token: str = ""
    timeout: float = DEFAULT_TIMEOUT

    # Mantém compatibilidade com os nomes usados pelo cliente atual.
    @property
    def netbox_url(self) -> str:
        return self.url

    @property
    def netbox_token(self) -> str:
        return self.token


class ConfigStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_config_path()

    def ensure_exists(self) -> None:
        if self.path.exists():
            try:
                self.path.chmod(0o600)
            except OSError as error:
                raise ConfigurationError(
                    f"Não foi possível proteger {self.path}: {error}"
                ) from error
            return
        self.save(Settings())

    def load(self, *, require_token: bool = False) -> Settings:
        self.ensure_exists()
        try:
            raw = yaml.safe_load(self.path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError) as error:
            raise ConfigurationError(
                f"Não foi possível ler {self.path}: {error}"
            ) from error

        if not isinstance(raw, dict):
            raise ConfigurationError(f"O arquivo {self.path} deve conter um mapa YAML")

        settings = self._parse(raw)
        if require_token and not settings.token:
            raise ConfigurationError(
                "Token não configurado. Execute 'netbox' para fazer login."
            )
        return settings

    def save(self, settings: Settings) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            self.path.parent.chmod(0o700)
            self.path.write_text(
                yaml.safe_dump(asdict(settings), sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )
            self.path.chmod(0o600)
        except OSError as error:
            raise ConfigurationError(
                f"Não foi possível salvar {self.path}: {error}"
            ) from error

    def save_token(self, token: str) -> Settings:
        settings = replace(self.load(), token=token.strip())
        self.save(settings)
        return settings

    @staticmethod
    def _parse(raw: dict[str, Any]) -> Settings:
        url = str(raw.get("url", DEFAULT_URL)).strip()
        token = str(raw.get("token", "")).strip()
        try:
            parsed_timeout = float(raw.get("timeout", DEFAULT_TIMEOUT))
        except (TypeError, ValueError) as error:
            raise ConfigurationError("timeout deve ser um número") from error

        if not url:
            raise ConfigurationError("url não pode ficar vazia")
        if parsed_timeout <= 0:
            raise ConfigurationError("timeout deve ser maior que zero")
        timeout = (
            int(parsed_timeout) if parsed_timeout.is_integer() else parsed_timeout
        )
        return Settings(url=url.rstrip("/"), token=token, timeout=timeout)
