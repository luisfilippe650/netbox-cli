from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, Mapping, TypedDict

from netbox_cli.exceptions import NetBoxCLIError


class CapacityError(NetBoxCLIError):
    """Dados insuficientes ou inválidos impedem um cálculo confiável."""


class RackFace(str, Enum):
    FRONT = "front"
    REAR = "rear"

    @classmethod
    def parse(cls, value: object, *, context: str) -> RackFace:
        normalized = str(value).strip().casefold()
        try:
            return cls(normalized)
        except ValueError as error:
            raise CapacityError(
                f"{context}: face '{value}' inválida. Use 'front' ou 'rear'."
            ) from error


class FaceCapacity(TypedDict):
    occupied_u: int | float
    free_u: int | float


class CapacityResult(TypedDict):
    total_u: int | float
    occupied_u: int | float
    free_u: int | float
    occupancy_percent: int | float
    front: FaceCapacity
    rear: FaceCapacity


@dataclass(frozen=True, slots=True)
class RackSpec:
    id: int
    height: Decimal
    starting_unit: Decimal

    @classmethod
    def from_api(cls, rack: Mapping[str, Any]) -> RackSpec:
        context = _resource_name("Rack", rack)
        rack_id = required_id(rack.get("id"), field="id", context=context)
        height = positive_decimal(
            rack.get("u_height"), field="u_height", context=context
        )
        starting_unit = positive_decimal(
            rack.get("starting_unit", 1), field="starting_unit", context=context
        )
        return cls(id=rack_id, height=height, starting_unit=starting_unit)


@dataclass(frozen=True, slots=True)
class DeviceTypeSpec:
    id: int
    height: Decimal
    full_depth: bool

    @classmethod
    def from_api(cls, device_type: Mapping[str, Any]) -> DeviceTypeSpec:
        context = _resource_name("Tipo de dispositivo", device_type)
        type_id = required_id(device_type.get("id"), field="id", context=context)
        height = non_negative_decimal(
            device_type.get("u_height"), field="u_height", context=context
        )
        full_depth = required_bool(
            device_type.get("is_full_depth", False),
            field="is_full_depth",
            context=context,
        )
        return cls(id=type_id, height=height, full_depth=full_depth)


@dataclass(frozen=True, slots=True)
class DevicePlacement:
    rack_id: int
    device_type_id: int
    position: Decimal
    face: RackFace

    @classmethod
    def from_api(cls, device: Mapping[str, Any]) -> DevicePlacement | None:
        rack_value = device.get("rack")
        position_value = device.get("position")
        if rack_value is None and position_value is None:
            return None

        context = _resource_name("Dispositivo", device)
        if rack_value is None or position_value is None:
            raise CapacityError(
                f"{context}: rack e position devem estar preenchidos em conjunto."
            )
        rack_id = required_id(rack_value, field="rack", context=context)
        type_id = required_id(
            device.get("device_type"), field="device_type", context=context
        )
        position = positive_decimal(position_value, field="position", context=context)
        face_value = choice_value(device.get("face")) or RackFace.FRONT.value
        face = RackFace.parse(face_value, context=context)
        return cls(rack_id, type_id, position, face)


def required_id(value: object, *, field: str, context: str) -> int:
    if isinstance(value, Mapping):
        value = value.get("id")
    if isinstance(value, bool):
        raise CapacityError(f"{context}: campo '{field}' deve conter um ID válido.")
    if not isinstance(value, (str, int, float, Decimal)):
        raise CapacityError(f"{context}: campo '{field}' deve conter um ID válido.")
    try:
        numeric_id = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise CapacityError(
            f"{context}: campo '{field}' deve conter um ID válido."
        ) from error
    if not numeric_id.is_finite() or numeric_id != numeric_id.to_integral_value():
        raise CapacityError(f"{context}: campo '{field}' deve conter um ID inteiro.")
    parsed = int(numeric_id)
    if parsed <= 0:
        raise CapacityError(f"{context}: campo '{field}' deve conter um ID positivo.")
    return parsed


def decimal_value(value: object, *, field: str, context: str) -> Decimal:
    if isinstance(value, bool):
        raise CapacityError(f"{context}: campo '{field}' deve ser numérico.")
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise CapacityError(f"{context}: campo '{field}' deve ser numérico.") from error
    if not parsed.is_finite():
        raise CapacityError(f"{context}: campo '{field}' deve ser um número finito.")
    return parsed


def positive_decimal(value: object, *, field: str, context: str) -> Decimal:
    parsed = decimal_value(value, field=field, context=context)
    if parsed <= 0:
        raise CapacityError(f"{context}: campo '{field}' deve ser maior que zero.")
    return parsed


def non_negative_decimal(value: object, *, field: str, context: str) -> Decimal:
    parsed = decimal_value(value, field=field, context=context)
    if parsed < 0:
        raise CapacityError(f"{context}: campo '{field}' não pode ser negativo.")
    return parsed


def required_bool(value: object, *, field: str, context: str) -> bool:
    if not isinstance(value, bool):
        raise CapacityError(f"{context}: campo '{field}' deve ser booleano.")
    return value


def choice_value(value: object) -> str | None:
    if isinstance(value, Mapping):
        value = value.get("value")
    return str(value) if value not in (None, "") else None


def _resource_name(label: str, resource: Mapping[str, Any]) -> str:
    identifier = resource.get("name") or resource.get("display") or resource.get("id")
    return f"{label} '{identifier}'" if identifier is not None else label
