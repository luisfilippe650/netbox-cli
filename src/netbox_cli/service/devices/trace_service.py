from __future__ import annotations

from typing import Any

from netbox_cli.client import NetBoxClient, get_all_results
from netbox_cli.service.devices.common import (
    INTERFACES_ENDPOINT,
    get_device,
    nested_value,
)
from netbox_cli.service.lookup import ResourceNotFoundError


class CableTraceService:
    def __init__(self, client: NetBoxClient) -> None:
        self.client = client

    def trace(
        self,
        name: str,
        interface_name: str,
        *,
        site_name: str | None = None,
    ) -> dict[str, Any]:
        device = get_device(self.client, name, site_name=site_name)
        interfaces = get_all_results(
            self.client,
            INTERFACES_ENDPOINT,
            params={"device_id": device["id"], "name": interface_name, "limit": 0},
        )
        exact = [
            item
            for item in interfaces
            if str(item.get("name", "")).casefold() == interface_name.casefold()
        ]

        if not exact:
            raise ResourceNotFoundError(
                f"Interface '{interface_name}' não encontrada em '{name}'."
            )

        interface = exact[0]
        raw_path = self.client.get(f"{INTERFACES_ENDPOINT}{interface['id']}/trace/")
        segments = raw_path if isinstance(raw_path, list) else []
        normalized = [_normalize_segment(item) for item in segments]
        normalized = [item for item in normalized if item is not None]

        return {
            "device": device.get("name") or name,
            "interface": interface.get("name") or interface_name,
            "connected": any(segment["far"] for segment in normalized),
            "segments": normalized,
        }


def _normalize_segment(segment: Any) -> dict[str, Any] | None:
    if not isinstance(segment, list) or len(segment) != 3:
        return None

    near_ends, cable, far_ends = segment
    normalized_cable = None

    if isinstance(cable, dict):
        normalized_cable = {
            "id": cable.get("id"),
            "label": cable.get("label") or cable.get("display"),
            "status": nested_value(cable.get("status"), "label"),
        }

    return {
        "near": [_normalize_termination(item) for item in _items(near_ends)],
        "cable": normalized_cable,
        "far": [_normalize_termination(item) for item in _items(far_ends)],
    }


def _items(group: Any) -> list[dict[str, Any]]:
    return (
        [item for item in group if isinstance(item, dict)]
        if isinstance(group, list)
        else []
    )


def _normalize_termination(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": str(item.get("object_type") or item.get("type") or "termination"),
        "device": nested_value(item.get("device"), "name"),
        "name": item.get("name") or item.get("display"),
    }
