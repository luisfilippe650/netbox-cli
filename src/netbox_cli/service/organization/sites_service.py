from typing import Any

from netbox_cli.client import NetBoxClient
from netbox_cli.client.pagination import get_all_results
from netbox_cli.schemas.organization.sites_dto import AddSite, UpdateSite
from netbox_cli.service.base_service import CRUDService
from netbox_cli.service.capacity import RACK_RESERVATIONS_ENDPOINT, site_capacities
from netbox_cli.service.capacity_types import CapacityError, required_id
from netbox_cli.service.lookup import get_by_name, resolve_resource_id


class SitesService(CRUDService[AddSite]):
    ENDPOINT = "/api/dcim/sites/"
    RACKS_ENDPOINT = "/api/dcim/racks/"
    DEVICES_ENDPOINT = "/api/dcim/devices/"
    DEVICE_TYPES_ENDPOINT = "/api/dcim/device-types/"
    REGIONS_ENDPOINT = "/api/dcim/regions/"

    def __init__(self, client: NetBoxClient) -> None:
        super().__init__(client)
        self._region_ids: dict[str, int] = {}

    def build_payload(self, item: AddSite | UpdateSite) -> dict[str, Any]:
        payload = super().build_payload(item)

        if isinstance(item.region, str):
            cache_key = item.region.casefold()

            if cache_key not in self._region_ids:
                self._region_ids[cache_key] = resolve_resource_id(
                    self.client,
                    self.REGIONS_ENDPOINT,
                    item.region,
                    resource_label="Região",
                )

            payload["region"] = self._region_ids[cache_key]

        return payload

    def status(self, name: str) -> dict[str, Any]:
        site = get_by_name(self.client, self.ENDPOINT, name, resource_label="Site")
        site_id = site["id"]
        racks = get_all_results(
            self.client,
            self.RACKS_ENDPOINT,
            params={"site_id": site_id, "limit": 0},
        )
        devices = get_all_results(
            self.client,
            self.DEVICES_ENDPOINT,
            params={"site_id": site_id, "limit": 0},
        )
        type_ids = _device_type_ids(devices)
        device_types = (
            get_all_results(
                self.client,
                self.DEVICE_TYPES_ENDPOINT,
                params={"id": type_ids, "limit": 0},
            )
            if type_ids
            else []
        )
        reservations = get_all_results(
            self.client,
            RACK_RESERVATIONS_ENDPOINT,
            params={"site_id": site_id, "limit": 0},
        )
        capacities = list(
            site_capacities(racks, devices, device_types, reservations).values()
        )
        total_u = sum(float(item["total_u"]) for item in capacities)
        occupied_u = sum(float(item["occupied_u"]) for item in capacities)
        manufacturers: dict[str, int] = {}

        for device in devices:
            device_type = device.get("device_type")
            manufacturer = (
                device_type.get("manufacturer")
                if isinstance(device_type, dict)
                else None
            )
            manufacturer_name = _value(manufacturer) or "Não informado"
            key = str(manufacturer_name)
            manufacturers[key] = manufacturers.get(key, 0) + 1

        return {
            "site": {
                "id": site_id,
                "name": site.get("name") or site.get("display"),
                "status": _value(site.get("status")),
            },
            "racks": len(racks),
            "devices": len(devices),
            "capacity": {
                "total_u": _clean(total_u),
                "occupied_u": _clean(occupied_u),
                "free_u": _clean(max(total_u - occupied_u, 0)),
                "occupancy_percent": (
                    round(occupied_u / total_u * 100, 2) if total_u else 0
                ),
            },
            "manufacturers": [
                {"name": manufacturer, "devices": count}
                for manufacturer, count in sorted(manufacturers.items())
            ],
        }


def _value(value: Any) -> Any:
    if isinstance(value, dict):
        return value.get("name") or value.get("label") or value.get("display")

    return value


def _clean(value: float) -> int | float:
    return int(value) if value.is_integer() else value


def _device_type_ids(devices: list[dict[str, Any]]) -> list[int]:
    type_ids: set[int] = set()

    for device in devices:
        device_type = device.get("device_type")

        if device_type is None:
            identifier = device.get("name") or device.get("id") or "desconhecido"

            raise CapacityError(
                f"Dispositivo '{identifier}': device_type não foi informado pela API."
            )

        identifier = device.get("name") or device.get("id") or "desconhecido"
        type_ids.add(
            required_id(
                device_type,
                field="device_type",
                context=f"Dispositivo '{identifier}'",
            )
        )

    return sorted(type_ids)
