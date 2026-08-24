from __future__ import annotations

import sys
import time
from typing import Any
from urllib.parse import urlsplit

import requests

from netbox_cli.exceptions import NetBoxCLIError


class NetBoxClientError(NetBoxCLIError):
    """Erro ao comunicar com a API do NetBox."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        method: str | None = None,
        endpoint: str | None = None,
        timeout: float | None = None,
        attempts: int = 1,
        cause: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.method = method
        self.endpoint = endpoint
        self.timeout = timeout
        self.attempts = attempts
        self.cause = cause


def _format_http_detail(detail: Any) -> str:
    if isinstance(detail, dict):
        if "detail" in detail:
            return str(detail["detail"])

        parts = []

        for field, messages in detail.items():
            if isinstance(messages, list):
                messages = ", ".join(str(message) for message in messages)

            parts.append(f"{field}: {messages}")

        return "\n".join(parts)

    return str(detail).strip()


class NetBoxClient:
    def __init__(
        self,
        base_url: str,
        token: str = "",
        timeout: float = 15,
        retries: int = 2,
        backoff: float = 0.5,
        verbose: bool = False,
        debug: bool = False,
    ) -> None:
        if not base_url:
            raise ValueError("A URL do NetBox é obrigatória")

        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retries = max(retries, 0)
        self.backoff = max(backoff, 0)
        self.verbose = verbose or debug
        self.debug = debug

        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

        if token:
            auth_scheme = "Bearer" if token.startswith("nbt_") else "Token"
            self.session.headers["Authorization"] = f"{auth_scheme} {token}"

    def request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> Any:
        url = self._request_url(endpoint)
        request_method = method.upper()
        max_attempts = self.retries + 1
        started_at = time.monotonic()

        for attempt in range(1, max_attempts + 1):
            self._log(
                f"{request_method} {endpoint} • tentativa {attempt}/{max_attempts} "
                f"• timeout {self.timeout}s"
            )

            try:
                response = self.session.request(
                    method=request_method,
                    url=url,
                    timeout=self.timeout,
                    **kwargs,
                )
                response.raise_for_status()
            except (requests.Timeout, requests.ConnectionError) as error:
                if self._retry_request(request_method, attempt, max_attempts, error):
                    continue

                kind = "Timeout" if isinstance(error, requests.Timeout) else "Conexão"
                raise self._communication_error(
                    kind,
                    request_method,
                    endpoint,
                    attempt,
                    error,
                ) from error
            except requests.HTTPError as error:
                response = error.response
                status = response.status_code if response is not None else None

                if (
                    status in {429, 500, 502, 503, 504}
                    and self._retry_request(
                        request_method,
                        attempt,
                        max_attempts,
                        error,
                        response=response,
                    )
                ):
                    continue

                raise self._http_error(
                    request_method,
                    endpoint,
                    attempt,
                    error,
                ) from error
            except requests.RequestException as error:
                raise self._communication_error(
                    "Requisição",
                    request_method,
                    endpoint,
                    attempt,
                    error,
                ) from error

            elapsed = time.monotonic() - started_at
            self._log(
                f"{request_method} {endpoint} • HTTP {response.status_code} "
                f"• {elapsed:.3f}s"
            )

            if response.status_code == 204 or not response.content:
                return None

            try:
                return response.json()
            except ValueError:
                return response.text

        raise RuntimeError("fluxo de tentativas HTTP terminou inesperadamente")

    def _retry_request(
        self,
        method: str,
        attempt: int,
        max_attempts: int,
        error: requests.RequestException,
        *,
        response: requests.Response | None = None,
    ) -> bool:
        if attempt >= max_attempts:
            return False

        if method not in {"GET", "HEAD", "OPTIONS"}:
            self._log(
                f"{method} não será repetido automaticamente para evitar "
                "duplicação de mutações."
            )

            return False

        delay = self._retry_delay(attempt, response)
        self._log(
            f"Falha transitória: {_summarize_exception(error)}. "
            f"Nova tentativa em {delay:g}s."
        )

        if delay:
            time.sleep(delay)

        return True

    def _retry_delay(
        self, attempt: int, response: requests.Response | None
    ) -> float:
        if response is not None:
            retry_after = response.headers.get("Retry-After")

            if retry_after:
                try:
                    return max(float(retry_after), 0)
                except ValueError:
                    pass

        return self.backoff * (2 ** (attempt - 1))

    def _communication_error(
        self,
        kind: str,
        method: str,
        endpoint: str,
        attempts: int,
        error: requests.RequestException,
    ) -> NetBoxClientError:
        cause = _summarize_exception(error)
        message = _diagnostic_message(
            f"Falha de {kind.lower()} ao comunicar com o NetBox.",
            method=method,
            endpoint=endpoint,
            timeout=self.timeout,
            attempts=attempts,
            cause=cause,
        )

        return NetBoxClientError(
            message,
            method=method,
            endpoint=endpoint,
            timeout=self.timeout,
            attempts=attempts,
            cause=cause,
        )

    def _http_error(
        self,
        method: str,
        endpoint: str,
        attempts: int,
        error: requests.HTTPError,
    ) -> NetBoxClientError:
        response = error.response
        status = response.status_code if response is not None else None
        cause = _summarize_exception(error)
        detail = ""

        if response is not None:
            try:
                detail = _format_http_detail(response.json())
            except ValueError:
                detail = _format_http_detail(response.text)

        summary = f"NetBox respondeu com HTTP {status}."

        if detail:
            summary = f"{summary}\nDetalhe: {detail}"

        message = _diagnostic_message(
            summary,
            method=method,
            endpoint=endpoint,
            timeout=self.timeout,
            attempts=attempts,
            cause=cause,
        )

        return NetBoxClientError(
            message,
            status_code=status,
            method=method,
            endpoint=endpoint,
            timeout=self.timeout,
            attempts=attempts,
            cause=cause,
        )

    def _log(self, message: str) -> None:
        if self.verbose:
            print(f"[netbox] {message}", file=sys.stderr)

    def _request_url(self, endpoint: str) -> str:
        try:
            parsed_endpoint = urlsplit(endpoint)
        except ValueError as error:
            raise NetBoxClientError(
                "O NetBox retornou uma página de continuação inválida"
            ) from error

        if not parsed_endpoint.scheme and not parsed_endpoint.netloc:
            return f"{self.base_url}/{endpoint.lstrip('/')}"

        try:
            parsed_base = urlsplit(self.base_url)
            unexpected_origin = _origin(parsed_endpoint) != _origin(parsed_base)
        except ValueError as error:
            raise NetBoxClientError(
                "O NetBox retornou uma página de continuação inválida"
            ) from error

        if parsed_endpoint.username is not None or parsed_endpoint.password is not None:
            unexpected_origin = True

        if unexpected_origin:
            raise NetBoxClientError(
                "O NetBox retornou uma página de continuação em uma origem inesperada"
            )

        return endpoint

    def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        return self.request("GET", endpoint, params=params)

    def post(
        self,
        endpoint: str,
        data: dict[str, Any],
    ) -> Any:
        return self.request("POST", endpoint, json=data)

    def patch(
        self,
        endpoint: str,
        data: dict[str, Any],
    ) -> Any:
        return self.request("PATCH", endpoint, json=data)

    def delete(self, endpoint: str) -> None:
        self.request("DELETE", endpoint)

    def close(self) -> None:
        self.session.close()


def _origin(parsed_url: Any) -> tuple[str, str | None, int | None]:
    default_port = 443 if parsed_url.scheme.lower() == "https" else 80

    return (
        parsed_url.scheme.lower(),
        parsed_url.hostname,
        parsed_url.port or default_port,
    )


def _summarize_exception(error: BaseException) -> str:
    message = " ".join(str(error).split()) or "sem mensagem adicional"

    if len(message) > 300:
        message = f"{message[:297]}..."

    return f"{type(error).__name__}: {message}"


def _diagnostic_message(
    summary: str,
    *,
    method: str,
    endpoint: str,
    timeout: float,
    attempts: int,
    cause: str,
) -> str:
    return (
        f"{summary}\n"
        f"Método: {method}\n"
        f"Endpoint: {endpoint}\n"
        f"Timeout por tentativa: {timeout}s\n"
        f"Tentativas realizadas: {attempts}\n"
        f"Causa: {cause}"
    )
