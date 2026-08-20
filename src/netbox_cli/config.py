from __future__ import annotations

import os
import stat
import tempfile
from dataclasses import asdict, dataclass, replace
from math import isfinite
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml

DEFAULT_URL = "http://localhost:8000"
DEFAULT_TIMEOUT = 15


class ConfigurationError(ValueError):
    """Configuração obrigatória ausente ou inválida."""


def default_config_path() -> Path:
    configured_path = os.getenv("NETBOX_CONFIG")
    if configured_path:
        return Path(configured_path).expanduser()
    config_root = Path(
        os.getenv("XDG_CONFIG_HOME", str(Path.home() / ".config"))
    ).expanduser()
    return config_root / "netbox-cli" / "config.yaml"


@dataclass(frozen=True, slots=True)
class Settings:
    url: str = DEFAULT_URL
    token: str = ""
    token_id: int | None = None
    token_url: str = ""
    timeout: float = DEFAULT_TIMEOUT

    # Mantém compatibilidade com os nomes usados pelo cliente atual.
    @property
    def netbox_url(self) -> str:
        return self.url

    @property
    def netbox_token(self) -> str:
        return self.token

    @property
    def token_version(self) -> int | None:
        if not self.token:
            return None
        return 2 if self.token.startswith("nbt_") else 1


class ConfigStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_config_path()

    def ensure_exists(self) -> None:
        if self.path.exists():
            try:
                current_mode = stat.S_IMODE(self.path.stat().st_mode)
                if current_mode != 0o600:
                    self.path.chmod(0o600)
            except OSError as error:
                raise ConfigurationError(
                    f"Não foi possível proteger {self.path}: {error}"
                ) from error
            return
        self.save(Settings())

    def load(
        self,
        *,
        require_token: bool = False,
        url: str | None = None,
        token: str | None = None,
        timeout: float | None = None,
        use_environment: bool = True,
    ) -> Settings:
        effective_url = (
            url
            if url is not None
            else os.getenv("NETBOX_URL") if use_environment else None
        )
        effective_token = (
            token
            if token is not None
            else os.getenv("NETBOX_TOKEN") if use_environment else None
        )
        environment_timeout = os.getenv("NETBOX_TIMEOUT") if use_environment else None
        effective_timeout: float | str | None = (
            timeout if timeout is not None else environment_timeout
        )

        # O arquivo só é dispensável quando todas as configurações possuem uma
        # fonte de maior precedência. Assim cada campo mantém a ordem
        # flags > ambiente > arquivo > padrão.
        file_exists = self.path.exists()
        read_file = file_exists and not (
            effective_url is not None
            and effective_token is not None
            and effective_timeout is not None
        )
        if read_file:
            self.ensure_exists()
        settings = self._parse(self._read_mapping()) if read_file else Settings()
        if effective_token is None:
            settings, migrated = self._enforce_token_origin(settings)
            if migrated and read_file:
                self.save(settings)

        raw = asdict(settings)
        if effective_url is not None:
            raw["url"] = effective_url
        if effective_timeout is not None:
            raw["timeout"] = effective_timeout

        if effective_token is not None:
            raw["token"] = effective_token
            raw["token_id"] = None
            raw["token_url"] = raw["url"] if str(effective_token).strip() else ""
        elif effective_url is not None and settings.token_url != str(raw["url"]).rstrip(
            "/"
        ):
            # Nunca envia um token do arquivo para uma URL sobrescrita.
            raw["token"] = ""
            raw["token_id"] = None
            raw["token_url"] = ""

        settings = self._parse(raw)
        if require_token and not settings.token:
            raise ConfigurationError(
                "Token não configurado. Execute 'netbox login' ou defina NETBOX_TOKEN."
            )
        return settings

    def save(self, settings: Settings) -> None:
        settings = self._validated_for_save(settings)
        serialized = yaml.safe_dump(
            asdict(settings), sort_keys=False, allow_unicode=True
        )
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            self.path.parent.chmod(0o700)
            self._atomic_write(serialized)
        except OSError as error:
            raise ConfigurationError(
                f"Não foi possível salvar {self.path}: {error}"
            ) from error

    def _read_mapping(self) -> dict[str, Any]:
        try:
            raw = yaml.safe_load(self.path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError) as error:
            raise ConfigurationError(
                f"Não foi possível ler {self.path}: {error}"
            ) from error
        if not isinstance(raw, dict):
            raise ConfigurationError(f"O arquivo {self.path} deve conter um mapa YAML")
        return raw

    @staticmethod
    def _enforce_token_origin(settings: Settings) -> tuple[Settings, bool]:
        if settings.token and settings.token_url != settings.url:
            # Sem uma origem comprovada, o segredo não pode chegar ao cliente HTTP.
            return replace(settings, token="", token_id=None, token_url=""), True
        if not settings.token and (settings.token_url or settings.token_id is not None):
            return replace(settings, token_id=None, token_url=""), True
        return settings, False

    @classmethod
    def _validated_for_save(cls, settings: Settings) -> Settings:
        settings = cls._parse(asdict(settings))
        if settings.token and settings.token_url != settings.url:
            raise ConfigurationError("token não pertence à URL configurada")
        return (
            replace(settings, token_id=None, token_url="")
            if not settings.token
            else settings
        )

    def _atomic_write(self, content: str) -> None:
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                delete=False,
            ) as temporary:
                temporary.write(content)
                temporary.flush()
                os.fsync(temporary.fileno())
                temporary_path = Path(temporary.name)
            temporary_path.chmod(0o600)
            os.replace(temporary_path, self.path)
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()

    def save_token(
        self,
        token: str,
        *,
        token_id: int | None = None,
        url: str | None = None,
        timeout: float | None = None,
    ) -> Settings:
        settings = self.load(
            url=url,
            timeout=timeout,
            use_environment=False,
        )
        normalized_token = token.strip()
        settings = replace(
            settings,
            token=normalized_token,
            token_id=token_id if normalized_token else None,
            token_url=settings.url if normalized_token else "",
        )
        self.save(settings)
        return settings

    def clear_token(self) -> Settings:
        settings = replace(
            self.load(use_environment=False),
            token="",
            token_id=None,
            token_url="",
        )
        self.save(settings)
        return settings

    def save_url(self, url: str) -> Settings:
        settings = self.load(use_environment=False)
        normalized_url = _validated_url(url, field_name="url")
        if normalized_url != settings.url:
            settings = replace(
                settings,
                url=normalized_url,
                token="",
                token_id=None,
                token_url="",
            )
        self.save(settings)
        return settings

    @staticmethod
    def _parse(raw: dict[str, Any]) -> Settings:
        raw_url = raw.get("url", DEFAULT_URL)
        raw_token = raw.get("token", "")
        raw_token_id = raw.get("token_id")
        raw_token_url = raw.get("token_url", "")
        if not isinstance(raw_url, str):
            raise ConfigurationError("url deve ser um texto")
        if raw_token is not None and not isinstance(raw_token, str):
            raise ConfigurationError("token deve ser um texto")
        if raw_token_id is not None and (
            isinstance(raw_token_id, bool)
            or not isinstance(raw_token_id, int)
            or raw_token_id <= 0
        ):
            raise ConfigurationError("token_id deve ser um inteiro maior que zero")
        if raw_token_url is not None and not isinstance(raw_token_url, str):
            raise ConfigurationError("token_url deve ser um texto")

        url = _validated_url(raw_url, field_name="url")
        token = raw_token.strip() if isinstance(raw_token, str) else ""
        token_url = (
            _validated_url(raw_token_url, field_name="token_url")
            if raw_token_url
            else ""
        )
        try:
            raw_timeout = raw.get("timeout", DEFAULT_TIMEOUT)
            if isinstance(raw_timeout, bool):
                raise TypeError
            parsed_timeout = float(raw_timeout)
        except (TypeError, ValueError) as error:
            raise ConfigurationError("timeout deve ser um número") from error

        if not isfinite(parsed_timeout) or parsed_timeout <= 0:
            raise ConfigurationError("timeout deve ser um número finito maior que zero")
        timeout = int(parsed_timeout) if parsed_timeout.is_integer() else parsed_timeout
        return Settings(
            url=url,
            token=token,
            token_id=raw_token_id,
            token_url=token_url,
            timeout=timeout,
        )


def _validated_url(value: str, *, field_name: str) -> str:
    normalized = value.strip().rstrip("/")
    if not normalized:
        raise ConfigurationError(f"{field_name} não pode ficar vazia")
    try:
        parsed_url = urlsplit(normalized)
        parsed_url.port
    except ValueError as error:
        raise ConfigurationError(
            f"{field_name} deve ser uma URL HTTP ou HTTPS válida"
        ) from error
    if (
        parsed_url.scheme not in {"http", "https"}
        or not parsed_url.hostname
        or parsed_url.username is not None
        or parsed_url.password is not None
        or parsed_url.query
        or parsed_url.fragment
    ):
        raise ConfigurationError(f"{field_name} deve ser uma URL HTTP ou HTTPS válida")
    return normalized
