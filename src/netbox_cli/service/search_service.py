from __future__ import annotations

from typing import Any

from netbox_cli.client.netbox_client import NetBoxClient
from netbox_cli.service.lookup import get_result_list


class SearchService:
    """Busca agregada nos recursos de infraestrutura mais usados."""

    RESOURCES = (
        ("device", "/api/dcim/devices/"),
        ("rack", "/api/dcim/racks/"),
        ("site", "/api/dcim/sites/"),
        ("location", "/api/dcim/locations/"),
        ("ip_address", "/api/ipam/ip-addresses/"),
    )

    def __init__(self, client: NetBoxClient) -> None:
        self.client = client

    def search(self, query: str, *, limit: int = 10) -> dict[str, Any]:
        results: list[dict[str, Any]] = []
        for resource_type, endpoint in self.RESOURCES:
            response = self.client.get(endpoint, params={"q": query, "limit": limit})
            results.extend(
                self._normalize(resource_type, item)
                for item in get_result_list(response)
            )
        return {"query": query, "count": len(results), "results": results}

    @staticmethod
    def _normalize(resource_type: str, item: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {
            "type": resource_type,
            "id": item.get("id"),
            "name": item.get("name") or item.get("address") or item.get("display"),
        }
        for field in ("rack", "site", "location", "status"):
            value = item.get(field)
            if isinstance(value, dict):
                value = (
                    value.get("name")
                    or value.get("label")
                    or value.get("display")
                )
            if value is not None:
                result[field] = value

        if resource_type == "device":
            primary = item.get("primary_ip4") or item.get("primary_ip")
            if isinstance(primary, dict):
                result["ip"] = primary.get("address") or primary.get("display")
        elif resource_type == "ip_address":
            result["address"] = item.get("address")
            assigned = item.get("assigned_object")
            if isinstance(assigned, dict):
                device = assigned.get("device")
                if isinstance(device, dict):
                    result["device"] = device.get("name") or device.get("display")
                result["interface"] = assigned.get("name") or assigned.get("display")
        return result
