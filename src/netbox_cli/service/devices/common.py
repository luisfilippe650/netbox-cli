from __future__ import annotations

from typing import Any

from netbox_cli.client import NetBoxClient
from netbox_cli.service.lookup import get_by_name

DEVICES_ENDPOINT = "/api/dcim/devices/"
INTERFACES_ENDPOINT = "/api/dcim/interfaces/"


def get_device(
    client: NetBoxClient,
    name: str,
    *,
    site_name: str | None = None,
) -> dict[str, Any]:
    filters = None

    if site_name:
        site = get_by_name(
            client,
            "/api/dcim/sites/",
            site_name,
            resource_label="Site",
        )
        filters = {"site_id": site["id"]}

    return get_by_name(
        client,
        DEVICES_ENDPOINT,
        name,
        resource_label="Dispositivo",
        filters=filters,
    )


def nested_value(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        return value.get(key) or value.get("display") or value.get("value")

    return value
