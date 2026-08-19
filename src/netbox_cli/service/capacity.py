from __future__ import annotations

from decimal import Decimal
from typing import Any

from netbox_cli.client import NetBoxClient
from netbox_cli.service.lookup import get_result_list


def rack_capacity(client: NetBoxClient, rack: dict[str, Any]) -> dict[str, Any]:
    """Calcula capacidade física e por face a partir da elevação do NetBox."""
    occupied_by_face: dict[str, set[float]] = {}
    for face in ("front", "rear"):
        response = client.get(
            f"/api/dcim/racks/{rack['id']}/elevation/",
            params={"face": face, "limit": 0},
        )
        occupied_by_face[face] = {
            float(unit["id"])
            for unit in get_result_list(response)
            if unit.get("occupied") and _is_number(unit.get("id"))
        }

    return capacity_from_slots(rack, occupied_by_face)


def site_capacities(
    racks: list[dict[str, Any]],
    devices: list[dict[str, Any]],
    device_types: list[dict[str, Any]],
    reservations: list[dict[str, Any]],
) -> dict[int, dict[str, Any]]:
    """Calcula todos os racks de um site sem consultar cada elevação."""
    rack_by_id = {
        int(rack["id"]): rack for rack in racks if rack.get("id") is not None
    }
    type_by_id = {
        int(device_type["id"]): device_type
        for device_type in device_types
        if device_type.get("id") is not None
    }
    slots = {
        rack_id: {"front": set(), "rear": set()} for rack_id in rack_by_id
    }

    for device in devices:
        rack_id = _nested_id(device.get("rack"))
        type_id = _nested_id(device.get("device_type"))
        position = device.get("position")
        device_type = type_by_id.get(type_id)
        if rack_id not in slots or position is None or not device_type:
            continue
        occupied = _device_slots(position, device_type.get("u_height"))
        face = _choice_value(device.get("face")) or "front"
        faces = ("front", "rear") if device_type.get("is_full_depth") else (face,)
        for rack_face in faces:
            if rack_face in slots[rack_id]:
                slots[rack_id][rack_face].update(occupied)

    for reservation in reservations:
        rack_id = _nested_id(reservation.get("rack"))
        if rack_id not in slots:
            continue
        for unit in reservation.get("units") or []:
            try:
                number = float(unit)
            except (TypeError, ValueError):
                continue
            for rack_face in ("front", "rear"):
                slots[rack_id][rack_face].update((number, number + 0.5))

    return {
        rack_id: capacity_from_slots(rack, slots[rack_id])
        for rack_id, rack in rack_by_id.items()
    }


def capacity_from_slots(
    rack: dict[str, Any], occupied_by_face: dict[str, set[float]]
) -> dict[str, Any]:
    total_u = float(rack.get("u_height") or 0)
    front_u = len(occupied_by_face["front"]) / 2
    rear_u = len(occupied_by_face["rear"]) / 2
    occupied_u = len(occupied_by_face["front"] | occupied_by_face["rear"]) / 2
    free_u = max(total_u - occupied_u, 0)
    return {
        "total_u": _clean_number(total_u),
        "occupied_u": _clean_number(occupied_u),
        "free_u": _clean_number(free_u),
        "occupancy_percent": round(occupied_u / total_u * 100, 2) if total_u else 0,
        "front": {
            "occupied_u": _clean_number(front_u),
            "free_u": _clean_number(max(total_u - front_u, 0)),
        },
        "rear": {
            "occupied_u": _clean_number(rear_u),
            "free_u": _clean_number(max(total_u - rear_u, 0)),
        },
    }


def _device_slots(position: Any, height: Any) -> set[float]:
    try:
        start = Decimal(str(position))
        slot_count = int(Decimal(str(height)) * 2)
    except (TypeError, ValueError):
        return set()
    return {float(start + Decimal("0.5") * offset) for offset in range(slot_count)}


def _nested_id(value: Any) -> int | None:
    value = value.get("id") if isinstance(value, dict) else value
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _choice_value(value: Any) -> str | None:
    if isinstance(value, dict):
        value = value.get("value")
    return str(value) if value else None


def _is_number(value: object) -> bool:
    try:
        float(str(value))
    except (TypeError, ValueError):
        return False
    return True


def _clean_number(value: float) -> int | float:
    return int(value) if value.is_integer() else value
