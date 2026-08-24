from __future__ import annotations

from typing import Any

from netbox_cli.client import NetBoxClient, get_all_results
from netbox_cli.service.devices.common import (
    INTERFACES_ENDPOINT,
    get_device,
    nested_value,
)


class DeviceInspectionService:
    IP_ADDRESSES_ENDPOINT = "/api/ipam/ip-addresses/"
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
        "inventory_items": ("inventory_item_count", "/api/dcim/inventory-items/"),
    }

    def __init__(self, client: NetBoxClient) -> None:
        self.client = client

    def inspect(self, name: str, *, site_name: str | None = None) -> dict[str, Any]:
        device = get_device(self.client, name, site_name=site_name)
        device_id = int(device["id"])
        interfaces = get_all_results(
            self.client,
            INTERFACES_ENDPOINT,
            params={"device_id": device_id, "limit": 0},
        )
        ip_addresses = get_all_results(
            self.client,
            self.IP_ADDRESSES_ENDPOINT,
            params={"device_id": device_id, "limit": 0},
        )
        components = self._components(device, device_id)

        return _inspection_result(device, interfaces, ip_addresses, components)

    def _components(
        self, device: dict[str, Any], device_id: int
    ) -> dict[str, list[dict[str, Any]]]:
        components: dict[str, list[dict[str, Any]]] = {}

        for name, (count_field, endpoint) in self.COMPONENT_ENDPOINTS.items():
            if not device.get(count_field):
                components[name] = []
                continue

            items = get_all_results(
                self.client, endpoint, params={"device_id": device_id, "limit": 0}
            )
            components[name] = [_normalize_component(item) for item in items]

        return components


def _inspection_result(
    device: dict[str, Any],
    interfaces: list[dict[str, Any]],
    ip_addresses: list[dict[str, Any]],
    components: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    return {
        "type": "device",
        "id": device.get("id"),
        "name": device.get("name") or device.get("display"),
        "role": nested_value(device.get("role"), "name"),
        "device_type": nested_value(device.get("device_type"), "model"),
        "manufacturer": _manufacturer(device.get("device_type")),
        "serial": device.get("serial"),
        "asset_tag": device.get("asset_tag"),
        "site": nested_value(device.get("site"), "name"),
        "location": nested_value(device.get("location"), "name"),
        "rack": nested_value(device.get("rack"), "name"),
        "position": device.get("position"),
        "face": nested_value(device.get("face"), "label"),
        "status": nested_value(device.get("status"), "label"),
        "platform": nested_value(device.get("platform"), "name"),
        "primary_ip": _ip(device.get("primary_ip")),
        "primary_ip4": _ip(device.get("primary_ip4")),
        "primary_ip6": _ip(device.get("primary_ip6")),
        "oob_ip": _ip(device.get("oob_ip")),
        "airflow": nested_value(device.get("airflow"), "label"),
        "description": device.get("description"),
        "custom_fields": device.get("custom_fields") or {},
        "tags": [nested_value(tag, "name") for tag in device.get("tags", [])],
        "created": device.get("created"),
        "last_updated": device.get("last_updated"),
        "interfaces": [_normalize_interface(item) for item in interfaces],
        "ip_addresses": [_normalize_ip(item) for item in ip_addresses],
        "components": components,
    }


def _normalize_interface(interface: dict[str, Any]) -> dict[str, Any]:
    endpoints = (
        interface.get("connected_endpoints") or interface.get("link_peers") or []
    )
    endpoint = endpoints[0] if isinstance(endpoints, list) and endpoints else None
    connected_device = None
    connected_interface = None

    if isinstance(endpoint, dict):
        connected_device = nested_value(endpoint.get("device"), "name")
        connected_interface = endpoint.get("name") or endpoint.get("display")

    return {
        "name": interface.get("name") or interface.get("display"),
        "label": interface.get("label"),
        "type": nested_value(interface.get("type"), "label"),
        "enabled": interface.get("enabled"),
        "mac_address": interface.get("mac_address"),
        "mtu": interface.get("mtu"),
        "management_only": interface.get("mgmt_only", False),
        "connected_device": connected_device,
        "connected_interface": connected_interface,
    }


def _normalize_ip(ip_address: dict[str, Any]) -> dict[str, Any]:
    return {
        "interface": nested_value(ip_address.get("assigned_object"), "name"),
        "address": ip_address.get("address"),
    }


def _normalize_component(item: dict[str, Any]) -> dict[str, Any]:
    endpoints = item.get("connected_endpoints") or item.get("link_peers") or []

    return {
        "id": item.get("id"),
        "name": item.get("name") or item.get("display"),
        "label": item.get("label"),
        "type": nested_value(item.get("type"), "label"),
        "description": item.get("description"),
        "connected_to": [
            {
                "device": nested_value(endpoint.get("device"), "name"),
                "name": endpoint.get("name") or endpoint.get("display"),
            }
            for endpoint in endpoints
            if isinstance(endpoint, dict)
        ],
    }


def _manufacturer(device_type: Any) -> Any:
    return (
        nested_value(device_type.get("manufacturer"), "name")
        if isinstance(device_type, dict)
        else None
    )


def _ip(value: Any) -> Any:
    if isinstance(value, dict):
        return value.get("address") or value.get("display")

    return value
