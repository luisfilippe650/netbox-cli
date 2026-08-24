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


def resolve_resource_id(
    client: NetBoxClient,
    endpoint: str,
    identifier: int | str,
    *,
    resource_label: str,
    fields: tuple[str, ...] = ("name", "slug"),
    filters: dict[str, Any] | None = None,
) -> int:
    """Resolve um relacionamento por ID, nome, slug ou outro campo exato."""
    if isinstance(identifier, int):
        return identifier

    normalized = identifier.strip()

    if normalized.isdecimal() and int(normalized) > 0:
        return int(normalized)

    resource = get_by_identifier(
        client,
        endpoint,
        normalized,
        resource_label=resource_label,
        fields=fields,
        filters=filters,
    )

    return int(resource["id"])


def get_by_identifier(
    client: NetBoxClient,
    endpoint: str,
    identifier: int | str,
    *,
    resource_label: str,
    fields: tuple[str, ...] = ("name", "slug"),
    filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Obtém um recurso por ID ou por um campo textual exato."""
    normalized = str(identifier).strip()

    if normalized.isdecimal() and int(normalized) > 0:
        return client.get(f"{endpoint}{int(normalized)}/")

    params = {**(filters or {}), "q": normalized, "limit": 0}
    results = get_all_results(client, endpoint, params=params)
    exact = [
        item
        for item in results
        if any(
            str(item.get(field, "")).casefold() == normalized.casefold()
            for field in fields
        )
    ]

    if not exact:
        for field in fields:
            params = {**(filters or {}), field: normalized, "limit": 0}
            candidates = get_all_results(client, endpoint, params=params)

            for item in candidates:
                matches = (
                    str(item.get(field, "")).casefold() == normalized.casefold()
                )

                if item not in exact and matches:
                    exact.append(item)

    if not exact:
        supported_fields = " ou ".join(fields)
        raise ResourceNotFoundError(
            f"{resource_label} '{normalized}' não encontrado por {supported_fields}."
        )

    identifiers = {item.get("id") for item in exact}

    if len(identifiers) > 1:
        raise AmbiguousResourceError(
            f"Mais de um {resource_label.lower()} corresponde a '{normalized}'. "
            "Use o ID para eliminar a ambiguidade."
        )

    return exact[0]


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
    identifier: int | str,
    *,
    site_name: str | None = None,
    location_name: str | None = None,
) -> dict[str, Any]:
    filters: dict[str, Any] = {}

    if site_name:
        site = get_by_identifier(
            client,
            "/api/dcim/sites/",
            site_name,
            resource_label="Site",
        )
        filters["site_id"] = site["id"]

    if location_name:
        location = get_by_identifier(
            client,
            "/api/dcim/locations/",
            location_name,
            resource_label="Local",
            filters={"site_id": filters["site_id"]} if "site_id" in filters else None,
        )
        filters["location_id"] = location["id"]

    if _is_positive_id(identifier):
        rack = get_by_identifier(
            client,
            "/api/dcim/racks/",
            identifier,
            resource_label="Rack",
            fields=("name",),
        )
        _validate_rack_scope(rack, filters)
    else:
        rack = get_by_name(
            client,
            "/api/dcim/racks/",
            str(identifier).strip(),
            resource_label="Rack",
            filters=filters,
        )

    return rack


def _validate_rack_scope(rack: dict[str, Any], filters: dict[str, Any]) -> None:
    """Garante que uma busca direta por ID respeite o escopo informado."""
    expected_site = filters.get("site_id")
    expected_location = filters.get("location_id")

    if expected_site is not None and _related_id(rack.get("site")) != expected_site:
        raise ResourceNotFoundError("O rack informado não pertence ao site selecionado.")

    if (
        expected_location is not None
        and _related_id(rack.get("location")) != expected_location
    ):
        raise ResourceNotFoundError(
            "O rack informado não pertence à localização selecionada."
        )


def _related_id(value: Any) -> Any:
    if isinstance(value, dict):
        return value.get("id")

    return value


def _is_positive_id(identifier: int | str) -> bool:
    normalized = str(identifier).strip()
    return normalized.isdecimal() and int(normalized) > 0
