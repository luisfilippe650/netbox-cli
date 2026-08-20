from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Iterable, Mapping, Sequence

from netbox_cli.client import NetBoxClient, get_all_results
from netbox_cli.service.capacity_types import (
    CapacityError,
    CapacityResult,
    DevicePlacement,
    DeviceTypeSpec,
    RackFace,
    RackSpec,
    decimal_value,
    required_id,
)

RACK_RESERVATIONS_ENDPOINT = "/api/dcim/rack-reservations/"
HALF_UNIT = Decimal("0.5")


@dataclass(slots=True)
class RackOccupancy:
    front: set[Decimal] = field(default_factory=set)
    rear: set[Decimal] = field(default_factory=set)

    def slots(self, face: RackFace) -> set[Decimal]:
        return self.front if face is RackFace.FRONT else self.rear

    def reserve_both_faces(self, slots: Iterable[Decimal]) -> None:
        # Reservas representam espaço físico e por isso bloqueiam as duas faces.
        reserved = set(slots)
        self.front.update(reserved)
        self.rear.update(reserved)

    def as_dict(self) -> dict[str, set[Decimal]]:
        return {RackFace.FRONT.value: self.front, RackFace.REAR.value: self.rear}


def rack_capacity(
    client: NetBoxClient, rack: Mapping[str, Any]
) -> CapacityResult:
    rack_spec = RackSpec.from_api(rack)
    occupied = rack_occupancy(client, rack)
    return capacity_from_slots(rack_spec, occupied)


def rack_occupancy(
    client: NetBoxClient,
    rack: Mapping[str, Any],
    *,
    faces: tuple[str, ...] = (RackFace.FRONT.value, RackFace.REAR.value),
) -> dict[str, set[Decimal]]:
    rack_spec = RackSpec.from_api(rack)
    requested_faces = tuple(
        RackFace.parse(face, context="Consulta de ocupação") for face in faces
    )
    occupancy = RackOccupancy()

    for face in requested_faces:
        units = get_all_results(
            client,
            f"/api/dcim/racks/{rack_spec.id}/elevation/",
            params={"face": face.value, "limit": 0},
        )
        occupancy.slots(face).update(_occupied_slots(units, rack_spec.id))

    reservations = get_all_results(
        client,
        RACK_RESERVATIONS_ENDPOINT,
        params={"rack_id": rack_spec.id, "limit": 0},
    )
    reserved = set().union(*(_reservation_slots(item) for item in reservations))
    for face in requested_faces:
        occupancy.slots(face).update(reserved)
    return {face.value: occupancy.slots(face) for face in requested_faces}


def site_capacities(
    racks: Sequence[Mapping[str, Any]],
    devices: Sequence[Mapping[str, Any]],
    device_types: Sequence[Mapping[str, Any]],
    reservations: Sequence[Mapping[str, Any]],
) -> dict[int, CapacityResult]:
    """Calcula o site inteiro e falha com contexto se a API estiver incoerente."""
    rack_specs = [RackSpec.from_api(rack) for rack in racks]
    rack_by_id = {rack.id: rack for rack in rack_specs}
    type_specs = [DeviceTypeSpec.from_api(item) for item in device_types]
    type_by_id = {device_type.id: device_type for device_type in type_specs}
    occupancy_by_rack = {rack.id: RackOccupancy() for rack in rack_specs}

    for device in devices:
        placement = DevicePlacement.from_api(device)
        if placement is None:
            continue
        if placement.rack_id not in occupancy_by_rack:
            raise CapacityError(
                f"Dispositivo no rack {placement.rack_id}: rack não retornado pela API."
            )
        device_type = type_by_id.get(placement.device_type_id)
        if device_type is None:
            raise CapacityError(
                "Dispositivo com tipo "
                f"{placement.device_type_id}: tipo não retornado pela API."
            )
        occupied = _device_slots(placement, device_type)
        faces = tuple(RackFace) if device_type.full_depth else (placement.face,)
        for face in faces:
            occupancy_by_rack[placement.rack_id].slots(face).update(occupied)

    for reservation in reservations:
        context = _reservation_context(reservation)
        rack_id = required_id(reservation.get("rack"), field="rack", context=context)
        if rack_id not in occupancy_by_rack:
            raise CapacityError(f"{context}: rack {rack_id} não retornado pela API.")
        occupancy_by_rack[rack_id].reserve_both_faces(
            _reservation_slots(reservation)
        )

    return {
        rack_id: capacity_from_slots(rack, occupancy_by_rack[rack_id].as_dict())
        for rack_id, rack in rack_by_id.items()
    }


def capacity_from_slots(
    rack: RackSpec,
    occupied_by_face: Mapping[str, set[Decimal]],
) -> CapacityResult:
    front = occupied_by_face.get(RackFace.FRONT.value)
    rear = occupied_by_face.get(RackFace.REAR.value)
    if front is None or rear is None:
        raise CapacityError("Ocupação do rack deve informar as faces front e rear.")

    front_u = Decimal(len(front)) * HALF_UNIT
    rear_u = Decimal(len(rear)) * HALF_UNIT
    occupied_u = Decimal(len(front | rear)) * HALF_UNIT
    free_u = max(rack.height - occupied_u, Decimal(0))
    return {
        "total_u": _clean_number(rack.height),
        "occupied_u": _clean_number(occupied_u),
        "free_u": _clean_number(free_u),
        "occupancy_percent": (
            float(round(occupied_u / rack.height * 100, 2))
        ),
        "front": {
            "occupied_u": _clean_number(front_u),
            "free_u": _clean_number(max(rack.height - front_u, Decimal(0))),
        },
        "rear": {
            "occupied_u": _clean_number(rear_u),
            "free_u": _clean_number(max(rack.height - rear_u, Decimal(0))),
        },
    }


def _occupied_slots(
    units: Sequence[Mapping[str, Any]], rack_id: int
) -> set[Decimal]:
    occupied: set[Decimal] = set()
    for unit in units:
        if not unit.get("occupied"):
            continue
        occupied.add(
            decimal_value(
                unit.get("id"),
                field="id",
                context=f"Unidade ocupada do rack {rack_id}",
            )
        )
    return occupied


def _device_slots(
    placement: DevicePlacement, device_type: DeviceTypeSpec
) -> set[Decimal]:
    if device_type.height == 0:
        raise CapacityError(
            f"Tipo de dispositivo {device_type.id}: dispositivo posicionado não pode ter 0U."
        )
    slot_count = int(device_type.height / HALF_UNIT)
    if device_type.height % HALF_UNIT:
        raise CapacityError(
            f"Tipo de dispositivo {device_type.id}: u_height deve ser múltiplo de 0.5."
        )
    return {
        placement.position + HALF_UNIT * offset for offset in range(slot_count)
    }


def _reservation_slots(reservation: Mapping[str, Any]) -> set[Decimal]:
    context = _reservation_context(reservation)
    raw_units = reservation.get("units") or []
    if not isinstance(raw_units, list):
        raise CapacityError(f"{context}: campo 'units' deve ser uma lista.")
    slots: set[Decimal] = set()
    for raw_unit in raw_units:
        unit = decimal_value(raw_unit, field="units", context=context)
        if unit <= 0:
            raise CapacityError(f"{context}: unidades devem ser maiores que zero.")
        slots.update((unit, unit + HALF_UNIT))
    return slots


def _reservation_context(reservation: Mapping[str, Any]) -> str:
    identifier = reservation.get("id")
    return f"Reserva de rack '{identifier}'" if identifier is not None else "Reserva de rack"


def _clean_number(value: Decimal) -> int | float:
    return int(value) if value == value.to_integral_value() else float(value)
