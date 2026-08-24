from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from netbox_cli.client import NetBoxClient, get_all_results
from netbox_cli.service.devices.inspection_service import DeviceInspectionService
from netbox_cli.service.lookup import get_by_name, get_scoped_rack


@dataclass(slots=True)
class TreeNode:
    type: str
    id: object
    name: str
    children: list[TreeNode] = field(default_factory=list)
    position: object | None = None
    status: object | None = None

    def add(self, child: TreeNode) -> None:
        self.children.append(child)

    def sort(self) -> None:
        self.children.sort(key=lambda item: item.name.casefold())

        for child in self.children:
            child.sort()

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "type": self.type,
            "id": self.id,
            "name": self.name,
            "children": [child.as_dict() for child in self.children],
        }

        if self.type == "device":
            result["position"] = self.position
            result["status"] = self.status

        return result


class InfrastructureService:
    """Monta uma hierarquia independente do formato visual da CLI."""

    ENDPOINTS = {
        "region": "/api/dcim/regions/",
        "site": "/api/dcim/sites/",
        "location": "/api/dcim/locations/",
        "rack": "/api/dcim/racks/",
        "device": "/api/dcim/devices/",
    }

    def __init__(self, client: NetBoxClient) -> None:
        self.client = client

    def tree(self, *, site_name: str | None = None) -> dict[str, Any]:
        if site_name:
            site = get_by_name(
                self.client,
                self.ENDPOINTS["site"],
                site_name,
                resource_label="Site",
            )
            site_id = site["id"]
            resources = {
                "region": self._region_ancestry(site),
                "site": [site],
                "location": self._list("location", site_id=site_id),
                "rack": self._list("rack", site_id=site_id),
                "device": self._list("device", site_id=site_id),
            }
        else:
            resources = {kind: self._list(kind) for kind in self.ENDPOINTS}

        root = TreeNode("root", None, "NetBox")
        nodes = {
            kind: {
                item["id"]: _node(kind, item)
                for item in items
                if item.get("id") is not None
            }
            for kind, items in resources.items()
        }

        for item in resources["region"]:
            region_node = nodes["region"].get(item.get("id"))

            if not region_node:
                continue

            parent = nodes["region"].get(_id(item.get("parent")), root)
            parent.add(region_node)

        orphan_region = TreeNode("group", None, "Sem região")

        for item in resources["site"]:
            site_node = nodes["site"].get(item.get("id"))

            if not site_node:
                continue

            region_id = _id(item.get("region"))
            parent = nodes["region"].get(region_id, orphan_region)
            parent.add(site_node)

        if orphan_region.children:
            root.add(orphan_region)

        for item in resources["location"]:
            location_node = nodes["location"].get(item.get("id"))

            if not location_node:
                continue

            parent_id = _id(item.get("parent"))
            parent = nodes["location"].get(parent_id)

            if parent is None:
                parent = nodes["site"].get(_id(item.get("site")), root)

            parent.add(location_node)

        for item in resources["rack"]:
            rack_node = nodes["rack"].get(item.get("id"))

            if not rack_node:
                continue

            parent = nodes["location"].get(_id(item.get("location")))

            if parent is None:
                parent = nodes["site"].get(_id(item.get("site")), root)

            parent.add(rack_node)

        for item in resources["device"]:
            device_node = nodes["device"].get(item.get("id"))

            if not device_node:
                continue

            parent = nodes["rack"].get(_id(item.get("rack")))

            if parent is None:
                parent = nodes["location"].get(_id(item.get("location")))

            if parent is None:
                parent = nodes["site"].get(_id(item.get("site")), root)

            parent.add(device_node)

        root.sort()
        result = root.as_dict()
        result["counts"] = {kind + "s": len(items) for kind, items in resources.items()}

        return result

    def rack_tree(
        self,
        name: str,
        *,
        site_name: str | None = None,
        location_name: str | None = None,
    ) -> dict[str, Any]:
        """Monta a árvore de um rack e dos dispositivos nele instalados."""
        rack = get_scoped_rack(
            self.client,
            name,
            site_name=site_name,
            location_name=location_name,
        )
        devices = self._list("device", rack_id=rack["id"])
        children = [_node("device", device).as_dict() for device in devices]
        children.sort(key=lambda item: str(item.get("name", "")).casefold())

        return {
            "type": "rack",
            "id": rack.get("id"),
            "name": _name(rack),
            "site": _related_name(rack.get("site")),
            "location": _related_name(rack.get("location")),
            "status": _related_label(rack.get("status")),
            "u_height": rack.get("u_height"),
            "device_count": len(devices),
            "children": children,
        }

    def device_tree(
        self,
        name: str,
        *,
        site_name: str | None = None,
    ) -> dict[str, Any]:
        """Monta localização, interfaces, IPs e conexões de um dispositivo."""
        details = DeviceInspectionService(self.client).inspect(
            name,
            site_name=site_name,
        )
        children: list[dict[str, Any]] = []

        location_path = _device_location_path(details)

        if location_path:
            children.append(
                {
                    "type": "group",
                    "name": "Localização",
                    "children": [location_path],
                }
            )

        interface_nodes, assigned_addresses = _interface_nodes(details)

        if interface_nodes:
            children.append(
                {
                    "type": "group",
                    "name": "Interfaces e conexões",
                    "children": interface_nodes,
                }
            )

        unassigned_ips = [
            {
                "type": "ip",
                "name": str(ip.get("address") or "—"),
                "children": [],
            }
            for ip in details.get("ip_addresses", [])
            if isinstance(ip, dict) and str(ip.get("address")) not in assigned_addresses
        ]

        if unassigned_ips:
            children.append(
                {
                    "type": "group",
                    "name": "IPs sem interface",
                    "children": unassigned_ips,
                }
            )

        component_nodes = _component_nodes(details)

        if component_nodes:
            children.append(
                {
                    "type": "group",
                    "name": "Componentes e conexões",
                    "children": component_nodes,
                }
            )

        return {
            "type": "device",
            "id": details.get("id"),
            "name": details.get("name"),
            "position": details.get("position"),
            "status": details.get("status"),
            "children": children,
            "details": details,
        }

    def _list(self, kind: str, **filters: Any) -> list[dict[str, Any]]:
        return get_all_results(
            self.client,
            self.ENDPOINTS[kind],
            params={**filters, "limit": 0},
        )

    def _region_ancestry(self, site: dict[str, Any]) -> list[dict[str, Any]]:
        region_id = _id(site.get("region"))
        regions = []
        visited = set()

        while region_id is not None and region_id not in visited:
            visited.add(region_id)
            region = self.client.get(f"{self.ENDPOINTS['region']}{region_id}/")

            if not isinstance(region, dict):
                break

            regions.append(region)
            region_id = _id(region.get("parent"))

        return regions


def _node(kind: str, item: dict[str, Any]) -> TreeNode:
    status = item.get("status")

    return TreeNode(
        type=kind,
        id=item.get("id"),
        name=_name(item),
        position=item.get("position") if kind == "device" else None,
        status=(
            (status.get("label") if isinstance(status, dict) else status)
            if kind == "device"
            else None
        ),
    )


def _id(value: Any) -> Any:
    return value.get("id") if isinstance(value, dict) else value


def _name(item: dict[str, Any]) -> str:
    return str(item.get("name") or item.get("display") or item.get("id"))


def _related_name(value: Any) -> Any:
    if isinstance(value, dict):
        return value.get("name") or value.get("display")

    return value


def _related_label(value: Any) -> Any:
    if isinstance(value, dict):
        return value.get("label") or value.get("value")

    return value


def _device_location_path(details: dict[str, Any]) -> dict[str, Any] | None:
    levels = [
        ("site", details.get("site")),
        ("location", details.get("location")),
        ("rack", details.get("rack")),
    ]
    root: dict[str, Any] | None = None
    current: dict[str, Any] | None = None

    for node_type, value in levels:
        if not value:
            continue

        node: dict[str, Any] = {
            "type": node_type,
            "name": str(value),
            "children": [],
        }

        if node_type == "rack":
            node["position"] = details.get("position")

        if root is None:
            root = node

        if current is not None:
            current["children"].append(node)

        current = node

    return root


def _interface_nodes(
    details: dict[str, Any],
) -> tuple[list[dict[str, Any]], set[str]]:
    addresses_by_interface: dict[str, list[str]] = {}

    for ip in details.get("ip_addresses", []):
        if not isinstance(ip, dict) or not ip.get("interface") or not ip.get("address"):
            continue

        addresses_by_interface.setdefault(str(ip["interface"]), []).append(
            str(ip["address"])
        )

    assigned_addresses: set[str] = set()
    nodes = []

    for interface in details.get("interfaces", []):
        if not isinstance(interface, dict):
            continue

        interface_name = str(interface.get("name") or "—")
        children: list[dict[str, Any]] = []
        connected_device = interface.get("connected_device")
        connected_interface = interface.get("connected_interface")

        if connected_device or connected_interface:
            target = ":".join(
                str(value) for value in (connected_device, connected_interface) if value
            )
            children.append({"type": "connection", "name": target, "children": []})

        for address in addresses_by_interface.get(interface_name, []):
            assigned_addresses.add(address)
            children.append({"type": "ip", "name": address, "children": []})

        nodes.append(
            {
                "type": "interface",
                "name": interface_name,
                "enabled": interface.get("enabled"),
                "interface_type": interface.get("type"),
                "children": children,
            }
        )

    return nodes, assigned_addresses


def _component_nodes(details: dict[str, Any]) -> list[dict[str, Any]]:
    groups = []
    components = details.get("components")

    if not isinstance(components, dict):
        return groups

    for component_type, items in components.items():
        item_nodes = []

        for item in items if isinstance(items, list) else []:
            if not isinstance(item, dict):
                continue

            connections = [
                {
                    "type": "connection",
                    "name": ":".join(
                        str(value)
                        for value in (connection.get("device"), connection.get("name"))
                        if value
                    ),
                    "children": [],
                }
                for connection in item.get("connected_to", [])
                if isinstance(connection, dict)
            ]
            item_nodes.append(
                {
                    "type": "component",
                    "name": str(item.get("name") or item.get("id") or "—"),
                    "children": connections,
                }
            )

        if item_nodes:
            groups.append(
                {
                    "type": "group",
                    "name": component_type.replace("_", " ").title(),
                    "children": item_nodes,
                }
            )

    return groups
