from __future__ import annotations

from decimal import Decimal
from typing import Any

from netbox_cli.exceptions import NetBoxCLIError
from netbox_cli.schemas.devices import AddDevice
from netbox_cli.service.base_service import CRUDService
from netbox_cli.service.lookup import (
    ResourceNotFoundError,
    get_by_name,
    get_result_list,
    get_scoped_rack,
)


class RequiredCustomFieldsError(NetBoxCLIError):
    """Campos personalizados obrigatórios não foram informados."""


class DevicesService(CRUDService[AddDevice]):
    ENDPOINT = "/api/dcim/devices/"
    INTERFACES_ENDPOINT = "/api/dcim/interfaces/"
    IP_ADDRESSES_ENDPOINT = "/api/ipam/ip-addresses/"
    RACKS_ENDPOINT = "/api/dcim/racks/"
    CUSTOM_FIELDS_ENDPOINT = "/api/extras/custom-fields/"
    COMPONENT_ENDPOINTS = {
        "console_ports": ("console_port_count", "/api/dcim/console-ports/"),
        "console_server_ports": (
            "console_server_port_count",
            "/api/dcim/console-server-ports/",
        ),
        "power_ports": ("power_port_count", "/api/dcim/power-ports/"),
        "power_outlets": ("power_outlet_count", "/api/dcim/power-outlets/"),
        "front_ports": ("front_port_count", "/api/dcim/front-ports/"),
        "rear_ports": ("rear_port_count", "/api/dcim/rear-ports/"),
        "module_bays": ("module_bay_count", "/api/dcim/module-bays/"),
        "device_bays": ("device_bay_count", "/api/dcim/device-bays/"),
        "inventory_items": (
            "inventory_item_count",
            "/api/dcim/inventory-items/",
        ),
    }
    USES_SLUG = False

    def create(self, item: AddDevice) -> dict[str, Any]:
        self._validate_required_custom_fields(item.custom_fields)
        return self.client.post(self.ENDPOINT, self.build_payload(item))

    def build_payload(self, item: AddDevice) -> dict[str, Any]:
        payload = item.model_dump(mode="json", exclude_none=True)
        if item.position is not None:
            payload["face"] = "front"
        return payload

    def inspect(
        self, name: str, *, site_name: str | None = None
    ) -> dict[str, Any]:
        device = self._get_device(name, site_name=site_name)
        device_id = int(device["id"])
        interfaces = get_result_list(
            self.client.get(
                self.INTERFACES_ENDPOINT,
                params={"device_id": device_id, "limit": 0},
            )
        )
        ip_addresses = get_result_list(
            self.client.get(
                self.IP_ADDRESSES_ENDPOINT,
                params={"device_id": device_id, "limit": 0},
            )
        )
        components = {}
        for component, (count_field, endpoint) in self.COMPONENT_ENDPOINTS.items():
            if not device.get(count_field):
                components[component] = []
                continue
            response = self.client.get(
                endpoint, params={"device_id": device_id, "limit": 0}
            )
            components[component] = [
                _normalize_component(item) for item in get_result_list(response)
            ]
        return self._inspection_result(
            device, interfaces, ip_addresses, components=components
        )

    def move(
        self,
        name: str,
        *,
        rack_name: str,
        position: float,
        device_site_name: str | None = None,
        rack_site_name: str | None = None,
        rack_location_name: str | None = None,
    ) -> dict[str, Any]:
        self._validate_position(position)
        device = self._get_device(name, site_name=device_site_name)
        return self._place_device(
            device,
            name=name,
            rack_name=rack_name,
            position=position,
            rack_site_name=rack_site_name,
            rack_location_name=rack_location_name,
        )

    def _place_device(
        self,
        device: dict[str, Any],
        *,
        name: str,
        rack_name: str,
        position: float,
        rack_site_name: str | None,
        rack_location_name: str | None,
    ) -> dict[str, Any]:
        rack = get_scoped_rack(
            self.client,
            rack_name,
            site_name=rack_site_name,
            location_name=rack_location_name,
        )
        payload: dict[str, Any] = {
            "rack": rack["id"],
            "position": position,
            "face": "front",
        }

        # O rack determina o site/local válidos. Isso também permite mover entre sites.
        rack_site = rack.get("site")
        if isinstance(rack_site, dict) and rack_site.get("id") is not None:
            payload["site"] = rack_site["id"]
        rack_location = rack.get("location")
        payload["location"] = (
            rack_location.get("id") if isinstance(rack_location, dict) else None
        )

        updated = self.client.patch(f"{self.ENDPOINT}{device['id']}/", payload)
        return {
            "moved": True,
            "device": updated.get("name", name) if isinstance(updated, dict) else name,
            "rack": rack.get("name", rack_name),
            "position": position,
            "face": "front",
        }

    def allocate(
        self,
        name: str,
        *,
        rack_name: str,
        position: float,
        device_site_name: str | None = None,
        rack_site_name: str | None = None,
        rack_location_name: str | None = None,
    ) -> dict[str, Any]:
        self._validate_position(position)
        device = self._get_device(name, site_name=device_site_name)
        current_rack = device.get("rack")
        if current_rack is not None:
            rack_label = _nested_value(current_rack, "name") or "rack desconhecido"
            raise NetBoxCLIError(
                f"Dispositivo '{name}' já está alocado em '{rack_label}'. "
                "Use 'netbox device move' para alterar sua posição."
            )

        result = self._place_device(
            device,
            name=name,
            rack_name=rack_name,
            position=position,
            rack_site_name=rack_site_name,
            rack_location_name=rack_location_name,
        )
        result["allocated"] = result.pop("moved")
        return result

    def deallocate(
        self, name: str, *, site_name: str | None = None
    ) -> dict[str, Any]:
        device = self._get_device(name, site_name=site_name)
        previous_rack = _nested_value(device.get("rack"), "name")
        previous_position = device.get("position")
        updated = self.client.patch(
            f"{self.ENDPOINT}{device['id']}/",
            {"rack": None, "position": None, "face": None},
        )
        return {
            "deallocated": True,
            "device": updated.get("name", name) if isinstance(updated, dict) else name,
            "previous_rack": previous_rack,
            "previous_position": previous_position,
        }

    def trace(
        self,
        name: str,
        interface_name: str,
        *,
        site_name: str | None = None,
    ) -> dict[str, Any]:
        device = self._get_device(name, site_name=site_name)
        interfaces = get_result_list(
            self.client.get(
                self.INTERFACES_ENDPOINT,
                params={
                    "device_id": device["id"],
                    "name": interface_name,
                    "limit": 0,
                },
            )
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
        raw_path = self.client.get(f"{self.INTERFACES_ENDPOINT}{interface['id']}/trace/")
        segments = raw_path if isinstance(raw_path, list) else []
        normalized_segments = []
        for segment in segments:
            if not isinstance(segment, list) or len(segment) != 3:
                continue
            near_ends, cable, far_ends = segment
            if isinstance(cable, dict):
                normalized_cable = {
                    "id": cable.get("id"),
                    "label": cable.get("label") or cable.get("display"),
                    "status": _nested_value(cable.get("status"), "label"),
                }
            else:
                normalized_cable = None
            normalized_segments.append(
                {
                    "near": [
                        _normalize_termination(item)
                        for item in _termination_items(near_ends)
                    ],
                    "cable": normalized_cable,
                    "far": [
                        _normalize_termination(item)
                        for item in _termination_items(far_ends)
                    ],
                }
            )
        return {
            "device": device.get("name") or name,
            "interface": interface.get("name") or interface_name,
            "connected": any(segment["far"] for segment in normalized_segments),
            "segments": normalized_segments,
        }

    def _get_device(
        self, name: str, *, site_name: str | None = None
    ) -> dict[str, Any]:
        filters = None
        if site_name:
            site = get_by_name(
                self.client,
                "/api/dcim/sites/",
                site_name,
                resource_label="Site",
            )
            filters = {"site_id": site["id"]}
        return get_by_name(
            self.client,
            self.ENDPOINT,
            name,
            resource_label="Dispositivo",
            filters=filters,
        )

    @staticmethod
    def _validate_position(position: float) -> None:
        if Decimal(str(position)) % Decimal("0.5"):
            raise NetBoxCLIError("--position deve ser múltiplo de 0.5.")

    @staticmethod
    def _inspection_result(
        device: dict[str, Any],
        interfaces: list[dict[str, Any]],
        ip_addresses: list[dict[str, Any]],
        *,
        components: dict[str, list[dict[str, Any]]] | None = None,
    ) -> dict[str, Any]:
        normalized_interfaces = []
        for interface in interfaces:
            endpoints = (
                interface.get("connected_endpoints")
                or interface.get("link_peers")
                or []
            )
            endpoint = endpoints[0] if isinstance(endpoints, list) and endpoints else None
            connected_device = None
            connected_interface = None
            if isinstance(endpoint, dict):
                endpoint_device = endpoint.get("device")
                if isinstance(endpoint_device, dict):
                    connected_device = endpoint_device.get(
                        "name"
                    ) or endpoint_device.get("display")
                connected_interface = endpoint.get("name") or endpoint.get("display")
            normalized_interfaces.append(
                {
                    "name": interface.get("name") or interface.get("display"),
                    "label": interface.get("label"),
                    "type": _nested_value(interface.get("type"), "label"),
                    "enabled": interface.get("enabled"),
                    "mac_address": interface.get("mac_address"),
                    "mtu": interface.get("mtu"),
                    "management_only": interface.get("mgmt_only", False),
                    "connected_device": connected_device,
                    "connected_interface": connected_interface,
                }
            )

        normalized_ips = []
        for ip_address in ip_addresses:
            assigned = ip_address.get("assigned_object")
            interface_name = None
            if isinstance(assigned, dict):
                interface_name = assigned.get("name") or assigned.get("display")
            normalized_ips.append(
                {"interface": interface_name, "address": ip_address.get("address")}
            )

        return {
            "type": "device",
            "id": device.get("id"),
            "name": device.get("name") or device.get("display"),
            "role": _nested_value(device.get("role"), "name"),
            "device_type": _nested_value(device.get("device_type"), "model"),
            "manufacturer": _manufacturer(device.get("device_type")),
            "serial": device.get("serial"),
            "asset_tag": device.get("asset_tag"),
            "site": _nested_value(device.get("site"), "name"),
            "location": _nested_value(device.get("location"), "name"),
            "rack": _nested_value(device.get("rack"), "name"),
            "position": device.get("position"),
            "face": _nested_value(device.get("face"), "label"),
            "status": _nested_value(device.get("status"), "label"),
            "platform": _nested_value(device.get("platform"), "name"),
            "primary_ip": _ip(device.get("primary_ip")),
            "primary_ip4": _ip(device.get("primary_ip4")),
            "primary_ip6": _ip(device.get("primary_ip6")),
            "oob_ip": _ip(device.get("oob_ip")),
            "airflow": _nested_value(device.get("airflow"), "label"),
            "description": device.get("description"),
            "custom_fields": device.get("custom_fields") or {},
            "tags": [_nested_value(tag, "name") for tag in device.get("tags", [])],
            "created": device.get("created"),
            "last_updated": device.get("last_updated"),
            "interfaces": normalized_interfaces,
            "ip_addresses": normalized_ips,
            "components": components or {},
        }

    def _validate_required_custom_fields(
        self, custom_fields: dict[str, Any]
    ) -> None:
        response = self.client.get(
            self.CUSTOM_FIELDS_ENDPOINT,
            params={"object_type": "dcim.device", "limit": 0},
        )
        definitions = response.get("results", []) if isinstance(response, dict) else []
        missing = []
        for field in definitions:
            if not isinstance(field, dict) or not field.get("required"):
                continue
            name = str(field.get("name", ""))
            value = custom_fields.get(name)
            if name not in custom_fields or value is None or value == "" or value == []:
                label = field.get("label") or name
                missing.append(f"{name} ({label})" if label != name else name)

        if missing:
            raise RequiredCustomFieldsError(
                "Campos personalizados obrigatórios ausentes: " + ", ".join(missing)
            )


def _nested_value(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        return value.get(key) or value.get("display") or value.get("value")
    return value


def _manufacturer(device_type: Any) -> Any:
    if isinstance(device_type, dict):
        return _nested_value(device_type.get("manufacturer"), "name")
    return None


def _ip(value: Any) -> Any:
    if isinstance(value, dict):
        return value.get("address") or value.get("display")
    return value


def _normalize_component(item: dict[str, Any]) -> dict[str, Any]:
    endpoints = item.get("connected_endpoints") or item.get("link_peers") or []
    return {
        "id": item.get("id"),
        "name": item.get("name") or item.get("display"),
        "label": item.get("label"),
        "type": _nested_value(item.get("type"), "label"),
        "description": item.get("description"),
        "connected_to": [
            {
                "device": _nested_value(endpoint.get("device"), "name"),
                "name": endpoint.get("name") or endpoint.get("display"),
            }
            for endpoint in endpoints
            if isinstance(endpoint, dict)
        ],
    }


def _termination_items(*groups: Any) -> list[dict[str, Any]]:
    return [
        item
        for group in groups
        if isinstance(group, list)
        for item in group
        if isinstance(item, dict)
    ]


def _normalize_termination(item: dict[str, Any]) -> dict[str, Any]:
    device = item.get("device")
    device_name = _nested_value(device, "name")
    return {
        "type": str(item.get("object_type") or item.get("type") or "termination"),
        "device": device_name,
        "name": item.get("name") or item.get("display"),
    }
