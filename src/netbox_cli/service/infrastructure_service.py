from __future__ import annotations

from typing import Any

from netbox_cli.client import NetBoxClient
from netbox_cli.service.lookup import get_by_name, get_result_list


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
                "region": self._list("region"),
                "site": [site],
                "location": self._list("location", site_id=site_id),
                "rack": self._list("rack", site_id=site_id),
                "device": self._list("device", site_id=site_id),
            }
        else:
            resources = {kind: self._list(kind) for kind in self.ENDPOINTS}
        root = _node("root", None, "NetBox")
        nodes = {
            kind: {
                item["id"]: _node(kind, item.get("id"), _name(item), source=item)
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
            parent["children"].append(region_node)
        orphan_region = _node("group", None, "Sem região")
        for item in resources["site"]:
            site_node = nodes["site"].get(item.get("id"))
            if not site_node:
                continue
            region_id = _id(item.get("region"))
            parent = nodes["region"].get(region_id, orphan_region)
            parent["children"].append(site_node)
        if orphan_region["children"]:
            root["children"].append(orphan_region)

        for item in resources["location"]:
            location_node = nodes["location"].get(item.get("id"))
            if not location_node:
                continue
            parent_id = _id(item.get("parent"))
            parent = nodes["location"].get(parent_id)
            if parent is None:
                parent = nodes["site"].get(_id(item.get("site")), root)
            parent["children"].append(location_node)

        for item in resources["rack"]:
            rack_node = nodes["rack"].get(item.get("id"))
            if not rack_node:
                continue
            parent = nodes["location"].get(_id(item.get("location")))
            if parent is None:
                parent = nodes["site"].get(_id(item.get("site")), root)
            parent["children"].append(rack_node)

        for item in resources["device"]:
            device_node = nodes["device"].get(item.get("id"))
            if not device_node:
                continue
            parent = nodes["rack"].get(_id(item.get("rack")))
            if parent is None:
                parent = nodes["location"].get(_id(item.get("location")))
            if parent is None:
                parent = nodes["site"].get(_id(item.get("site")), root)
            parent["children"].append(device_node)

        _sort_tree(root)
        root["counts"] = {kind + "s": len(items) for kind, items in resources.items()}
        return root

    def _list(self, kind: str, **filters: Any) -> list[dict[str, Any]]:
        return get_result_list(
            self.client.get(
                self.ENDPOINTS[kind], params={**filters, "limit": 0}
            )
        )


def _node(
    kind: str,
    item_id: object,
    name: str,
    *,
    source: dict[str, Any] | None = None,
) -> dict[str, Any]:
    node: dict[str, Any] = {
        "type": kind,
        "id": item_id,
        "name": name,
        "children": [],
    }
    if kind == "device" and source:
        node["position"] = source.get("position")
        status = source.get("status")
        node["status"] = status.get("label") if isinstance(status, dict) else status
    return node


def _id(value: Any) -> Any:
    return value.get("id") if isinstance(value, dict) else value


def _name(item: dict[str, Any]) -> str:
    return str(item.get("name") or item.get("display") or item.get("id"))


def _sort_tree(node: dict[str, Any]) -> None:
    children = node.get("children", [])
    children.sort(key=lambda item: str(item.get("name", "")).casefold())
    for child in children:
        _sort_tree(child)
