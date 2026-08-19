from typing import Any

from netbox_cli.schemas.organization.sites_dto import AddSite
from netbox_cli.service.base_service import CRUDService
from netbox_cli.service.capacity import site_capacities
from netbox_cli.service.lookup import get_by_name, get_result_list


class SitesService(CRUDService[AddSite]):
    ENDPOINT = "/api/dcim/sites/"
    RACKS_ENDPOINT = "/api/dcim/racks/"
    DEVICES_ENDPOINT = "/api/dcim/devices/"
    DEVICE_TYPES_ENDPOINT = "/api/dcim/device-types/"
    RESERVATIONS_ENDPOINT = "/api/dcim/rack-reservations/"

    def status(self, name: str) -> dict[str, Any]:
        site = get_by_name(self.client, self.ENDPOINT, name, resource_label="Site")
        site_id = site["id"]
        racks = get_result_list(
            self.client.get(self.RACKS_ENDPOINT, params={"site_id": site_id, "limit": 0})
        )
        devices = get_result_list(
            self.client.get(
                self.DEVICES_ENDPOINT, params={"site_id": site_id, "limit": 0}
            )
        )
        type_ids = sorted(
            {
                int(device_type["id"])
                for device in devices
                if isinstance((device_type := device.get("device_type")), dict)
                and device_type.get("id") is not None
            }
        )
        device_types = get_result_list(
            self.client.get(
                self.DEVICE_TYPES_ENDPOINT,
                params={"id": type_ids, "limit": 0},
            )
        ) if type_ids else []
        reservations = get_result_list(
            self.client.get(
                self.RESERVATIONS_ENDPOINT,
                params={"site_id": site_id, "limit": 0},
            )
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
                device_type.get("manufacturer") if isinstance(device_type, dict) else None
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
                "occupancy_percent": round(occupied_u / total_u * 100, 2)
                if total_u
                else 0,
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
