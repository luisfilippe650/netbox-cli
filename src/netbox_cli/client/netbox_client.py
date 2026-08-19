from __future__ import annotations

from typing import Any

import requests

from netbox_cli.exceptions import NetBoxCLIError


class NetBoxClientError(NetBoxCLIError):
    """Erro ao comunicar com a API do NetBox."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


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
    ) -> None:
        if not base_url:
            raise ValueError("A URL do NetBox é obrigatória")

        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

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
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        try:
            response = self.session.request(
                method=method,
                url=url,
                timeout=self.timeout,
                **kwargs,
            )

            response.raise_for_status()

        except requests.Timeout as error:
            raise NetBoxClientError(
                f"O NetBox não respondeu dentro de {self.timeout} segundos"
            ) from error

        except requests.ConnectionError as error:
            raise NetBoxClientError(
                f"Não foi possível conectar ao NetBox em {self.base_url}"
            ) from error

        except requests.HTTPError as error:
            response = error.response

            if response is not None:
                try:
                    detail = response.json()
                except ValueError:
                    detail = response.text

                raise NetBoxClientError(
                    f"NetBox respondeu com HTTP {response.status_code}.\n"
                    f"{_format_http_detail(detail)}",
                    status_code=response.status_code,
                ) from error

            raise NetBoxClientError("O NetBox retornou um erro HTTP") from error

        except requests.RequestException as error:
            raise NetBoxClientError(
                f"Erro durante a comunicação com o NetBox: {error}"
            ) from error

        # DELETE costuma retornar 204 sem conteúdo
        if response.status_code == 204 or not response.content:
            return None

        try:
            return response.json()
        except ValueError:
            return response.text

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
