from __future__ import annotations

from typing import Any, Protocol

from netbox_cli.exceptions import NetBoxCLIError


class ReadClient(Protocol):
    """Contrato mínimo necessário para consultar recursos paginados."""

    def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> Any: ...


class PaginationError(NetBoxCLIError):
    """A API retornou uma paginação inválida ou cíclica."""


def get_result_list(response: Any) -> list[dict[str, Any]]:
    if not isinstance(response, dict):
        return []
    results = response.get("results", [])
    if not isinstance(results, list):
        return []
    return [item for item in results if isinstance(item, dict)]


def get_all_results(
    client: ReadClient,
    endpoint: str,
    *,
    params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Percorre todas as páginas sem expor paginação à camada de serviço."""
    response = client.get(endpoint, params=params)
    results = get_result_list(response)
    visited: set[str] = set()

    while isinstance(response, dict) and response.get("next"):
        next_url = response["next"]
        if not isinstance(next_url, str) or next_url in visited:
            raise PaginationError(
                "O NetBox retornou uma paginação inválida ou cíclica."
            )
        visited.add(next_url)
        response = client.get(next_url)
        results.extend(get_result_list(response))

    return results
