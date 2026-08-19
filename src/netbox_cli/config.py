from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


class ConfigurationError(ValueError):
    """Configuração obrigatória ausente ou inválida."""


@dataclass(frozen=True, slots=True)
class Settings:
    netbox_url: str
    netbox_token: str
    timeout: float = 15.0

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv(dotenv_path=os.getenv("NETBOX_ENV_FILE", ".env"))

        url = os.getenv("NETBOX_URL", "").strip()
        token = os.getenv("NETBOX_TOKEN", "").strip()

        missing = [
            name
            for name, value in (("NETBOX_URL", url), ("NETBOX_TOKEN", token))
            if not value
        ]
        if missing:
            raise ConfigurationError(
                f"Variável(is) obrigatória(s) ausente(s): {', '.join(missing)}"
            )

        try:
            timeout = float(os.getenv("NETBOX_TIMEOUT", "15"))
        except ValueError as error:
            raise ConfigurationError("NETBOX_TIMEOUT deve ser um número") from error

        if timeout <= 0:
            raise ConfigurationError("NETBOX_TIMEOUT deve ser maior que zero")

        return cls(netbox_url=url, netbox_token=token, timeout=timeout)
