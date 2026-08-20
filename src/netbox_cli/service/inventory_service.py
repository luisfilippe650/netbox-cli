from __future__ import annotations

from typing import Any

from netbox_cli.client.netbox_client import NetBoxClient
from netbox_cli.exceptions import NetBoxCLIError
from netbox_cli.client.pagination import get_all_results
from netbox_cli.service.lookup import get_by_name, get_scoped_rack


class InventoryFilterError(NetBoxCLIError):
    """O filtro do inventário é ausente ou conflitante."""


class InventoryService:
    DEVICES_ENDPOINT = "/api/dcim/devices/"
    SITES_ENDPOINT = "/api/dcim/sites/"
    RACKS_ENDPOINT = "/api/dcim/racks/"

    def __init__(self, client: NetBoxClient) -> None:
        self.client = client

    def inventory(
        self,
        *,
        site_name: str | None = None,
        rack_name: str | None = None,
        location_name: str | None = None,
    ) -> dict[str, Any]:
        if not site_name and not rack_name:
            raise InventoryFilterError("Informe --site ou --rack.")
        if location_name and not rack_name:
            raise InventoryFilterError("--location só pode ser usado com --rack.")

        if not rack_name:
            resource = get_by_name(
                self.client,
                self.SITES_ENDPOINT,
                site_name,
                resource_label="Site",
            )
            filter_type = "site"
            filter_value = resource.get("name", site_name)
            params = {"site_id": resource["id"], "limit": 0}
        else:
            resource = get_scoped_rack(
                self.client,
                rack_name,
                site_name=site_name,
                location_name=location_name,
            )
            filter_type = "rack"
            filter_value = resource.get("name", rack_name)
            params = {"rack_id": resource["id"], "limit": 0}

        devices = [
            self._normalize(item)
            for item in get_all_results(
                self.client, self.DEVICES_ENDPOINT, params=params
            )
        ]
        return {
            "filter": {"type": filter_type, "value": filter_value},
            "count": len(devices),
            "results": devices,
        }

    @staticmethod
    def _normalize(device: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": device.get("id"),
            "name": device.get("name") or device.get("display"),
            "role": _value(device.get("role")),
            "device_type": _value(device.get("device_type")),
            "site": _value(device.get("site")),
            "location": _value(device.get("location")),
            "rack": _value(device.get("rack")),
            "position": device.get("position"),
            "status": _value(device.get("status")),
            "primary_ip": _ip_value(
                device.get("primary_ip4")
                or device.get("primary_ip6")
                or device.get("primary_ip")
            ),
            "serial": device.get("serial") or "",
        }


def _value(value: Any) -> Any:
    if isinstance(value, dict):
        return value.get("name") or value.get("label") or value.get("display")
    return value


def _ip_value(value: Any) -> Any:
    if isinstance(value, dict):
        return value.get("address") or value.get("display")
    return value
