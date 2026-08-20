from decimal import Decimal

from netbox_cli.client.pagination import get_all_results
from netbox_cli.schemas.racks import AddRack
from netbox_cli.service.base_service import CRUDService
from netbox_cli.service.capacity import rack_capacity, rack_occupancy
from netbox_cli.service.capacity_types import (
    CapacityError,
    RackFace,
    RackSpec,
    decimal_value,
)
from netbox_cli.service.lookup import get_scoped_rack


class RacksService(CRUDService[AddRack]):
    ENDPOINT = "/api/dcim/racks/"
    USES_SLUG = False

    def capacity(
        self,
        name: str,
        *,
        site_name: str | None = None,
        location_name: str | None = None,
    ) -> dict[str, object]:
        rack = get_scoped_rack(
            self.client,
            name,
            site_name=site_name,
            location_name=location_name,
        )
        return {
            "rack": rack.get("name") or rack.get("display"),
            "site": _value(rack.get("site")),
            "location": _value(rack.get("location")),
            **rack_capacity(self.client, rack),
        }

    def elevation(
        self,
        name: str,
        *,
        face: str = "front",
        site_name: str | None = None,
        location_name: str | None = None,
    ) -> dict[str, object]:
        rack = get_scoped_rack(
            self.client,
            name,
            site_name=site_name,
            location_name=location_name,
        )
        rack_spec = RackSpec.from_api(rack)
        requested_face = RackFace.parse(face, context="Elevação do rack")
        units = get_all_results(
            self.client,
            f"{self.ENDPOINT}{rack_spec.id}/elevation/",
            params={"face": requested_face.value, "limit": 0},
        )
        return {
            "id": rack.get("id"),
            "name": rack.get("name") or rack.get("display"),
            "site": _value(rack.get("site")),
            "location": _value(rack.get("location")),
            "face": requested_face.value,
            "u_height": _number(rack_spec.height),
            "starting_unit": _number(rack_spec.starting_unit),
            "units": units,
        }

    def available(
        self,
        name: str,
        *,
        height: float,
        face: str = "front",
        site_name: str | None = None,
        location_name: str | None = None,
    ) -> dict[str, object]:
        requested_height = decimal_value(
            height, field="height", context="Consulta de disponibilidade"
        )
        if requested_height < Decimal("0.5") or requested_height % Decimal("0.5"):
            raise CapacityError(
                "Consulta de disponibilidade: height deve ser múltiplo de 0.5 "
                "e maior que zero."
            )
        requested_face = RackFace.parse(face, context="Consulta de disponibilidade")

        rack = get_scoped_rack(
            self.client,
            name,
            site_name=site_name,
            location_name=location_name,
        )
        rack_spec = RackSpec.from_api(rack)
        occupied = rack_occupancy(
            self.client, rack, faces=(requested_face.value,)
        )[requested_face.value]
        top_half_unit = rack_spec.starting_unit + rack_spec.height - Decimal("0.5")
        required_slots = int(requested_height / Decimal("0.5"))
        candidates: list[int | float] = []
        position = rack_spec.starting_unit
        while position + requested_height - Decimal("0.5") <= top_half_unit:
            slots = {
                position + Decimal("0.5") * offset
                for offset in range(required_slots)
            }
            if not slots.intersection(occupied):
                candidates.append(float(position))
            position += Decimal("0.5")
        return {
            "rack": rack.get("name") or rack.get("display"),
            "face": requested_face.value,
            "height": _number(requested_height),
            "count": len(candidates),
            "positions": candidates,
        }


def _value(value: object) -> object:
    if isinstance(value, dict):
        return value.get("name") or value.get("display")
    return value


def _number(value: Decimal) -> int | float:
    return int(value) if value == value.to_integral_value() else float(value)
