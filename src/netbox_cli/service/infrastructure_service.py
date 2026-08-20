from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from netbox_cli.client import NetBoxClient, get_all_results
from netbox_cli.service.lookup import get_by_name


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
