from __future__ import annotations

from typing import Any

from netbox_cli.client.netbox_client import NetBoxClient
from netbox_cli.client.pagination import (
    PaginationError,
    get_all_results,
    get_result_list,
)
from netbox_cli.exceptions import NetBoxCLIError


class ResourceNotFoundError(NetBoxCLIError):
    """Um recurso solicitado pelo nome não existe."""


class AmbiguousResourceError(NetBoxCLIError):
    """Mais de um recurso corresponde ao nome solicitado."""


# Reexportações de compatibilidade. Código novo deve importar de ``client.pagination``.


def get_by_name(
    client: NetBoxClient,
    endpoint: str,
    name: str,
    *,
    resource_label: str,
    filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve nomes exatamente, sem escolher silenciosamente entre duplicatas."""
    params = {**(filters or {}), "name": name, "limit": 0}
    results = get_all_results(client, endpoint, params=params)
    if not results:
        # Alguns filtros `name` do NetBox são case-sensitive. A busca geral
        # seguida da comparação local mantém a resolução exata sem exigir caixa.
        params = {**(filters or {}), "q": name, "limit": 0}
        results = get_all_results(client, endpoint, params=params)
    exact = [
        item
        for item in results
        if str(item.get("name", "")).casefold() == name.casefold()
    ]
    if not exact:
        raise ResourceNotFoundError(f"{resource_label} '{name}' não encontrado.")
    if len(exact) > 1:
        raise AmbiguousResourceError(
            f"Mais de um {resource_label.lower()} possui o nome '{name}'. "
            "Informe site/local para restringir a busca."
        )
    return exact[0]


def get_scoped_rack(
    client: NetBoxClient,
    name: str,
    *,
    site_name: str | None = None,
    location_name: str | None = None,
) -> dict[str, Any]:
    filters: dict[str, Any] = {}
    if site_name:
        site = get_by_name(
            client,
            "/api/dcim/sites/",
            site_name,
            resource_label="Site",
        )
        filters["site_id"] = site["id"]
    if location_name:
        location = get_by_name(
            client,
            "/api/dcim/locations/",
            location_name,
            resource_label="Local",
            filters={"site_id": filters["site_id"]} if "site_id" in filters else None,
        )
        filters["location_id"] = location["id"]
    return get_by_name(
        client,
        "/api/dcim/racks/",
        name,
        resource_label="Rack",
        filters=filters,
    )
