from decimal import Decimal
from typing import Any

from netbox_cli.client import NetBoxClient
from netbox_cli.client.pagination import get_all_results
from netbox_cli.exceptions import NetBoxCLIError
from netbox_cli.schemas.racks import AddRack, UpdateRack
from netbox_cli.service.base_service import CRUDService
from netbox_cli.service.capacity import rack_capacity, rack_occupancy
from netbox_cli.service.capacity_types import (
    CapacityError,
    RackFace,
    RackSpec,
    decimal_value,
)
from netbox_cli.service.lookup import get_scoped_rack, resolve_resource_id


class RacksService(CRUDService[AddRack]):
    ENDPOINT = "/api/dcim/racks/"
    USES_SLUG = False

    def __init__(self, client: NetBoxClient) -> None:
        super().__init__(client)
        self._location_ids: dict[tuple[int, str], int] = {}
        self._site_ids: dict[str, int] = {}

    def build_payload(self, item: AddRack | UpdateRack) -> dict[str, Any]:
        payload = item.model_dump(mode="json", exclude_none=True)
        site_id = self._resolve_site(item.site) if item.site is not None else None

        if site_id is not None:
            payload["site"] = site_id

        if isinstance(item.location, str):
            if site_id is None:
                raise NetBoxCLIError(
                    "site é necessário para resolver a localização pelo nome"
                )

            payload["location"] = self._resolve_location(item.location, site_id)

        return payload

    def ensure(
        self,
        item: AddRack,
        *,
        identity_field: str = "name",
        filters: dict[str, Any] | None = None,
        update_fields: set[str] | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        site_id = self._resolve_site(item.site)

        return super().ensure(
            item,
            identity_field=identity_field,
            filters={**(filters or {}), "site_id": site_id},
            update_fields=update_fields,
            dry_run=dry_run,
        )

    def update(self, item_id: int, item: UpdateRack) -> dict[str, Any]:
        resolved = self._resolve_update_location(item, item_id=item_id)

        return super().update(item_id, resolved)

    def changes_for(
        self, current: dict[str, Any], item: UpdateRack
    ) -> dict[str, Any]:
        resolved = self._resolve_update_location(item, current=current)

        return super().changes_for(current, resolved)

    def _resolve_update_location(
        self,
        item: UpdateRack,
        *,
        item_id: int | None = None,
        current: dict[str, Any] | None = None,
    ) -> UpdateRack:
        if not isinstance(item.location, str):
            return item

        site_id = self._resolve_site(item.site) if item.site is not None else None

        if site_id is None:
            if current is None:
                if item_id is None:
                    raise NetBoxCLIError(
                        "não foi possível identificar o rack a ser atualizado"
                    )

                current = self.get(item_id)

            site_id = _nested_id(current.get("site"))

        location_id = self._resolve_location(item.location, site_id)
        updates: dict[str, int] = {"location": location_id}

        if item.site is not None:
            updates["site"] = site_id

        return item.model_copy(update=updates)

    def _resolve_site(self, identifier: int | str) -> int:
        if isinstance(identifier, int):
            return identifier

        cache_key = identifier.casefold()

        if cache_key not in self._site_ids:
            self._site_ids[cache_key] = resolve_resource_id(
                self.client,
                "/api/dcim/sites/",
                identifier,
                resource_label="Site",
            )

        return self._site_ids[cache_key]

    def _resolve_location(self, name: str, site_id: int) -> int:
        cache_key = (site_id, name.casefold())

        if cache_key not in self._location_ids:
            self._location_ids[cache_key] = resolve_resource_id(
                self.client,
                "/api/dcim/locations/",
                name,
                resource_label="Localização",
                filters={"site_id": site_id},
            )

        return self._location_ids[cache_key]

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


def _nested_id(value: object) -> int:
    if isinstance(value, dict) and isinstance(value.get("id"), int):
        return value["id"]

    raise NetBoxCLIError("não foi possível identificar o site atual do rack")


def _number(value: Decimal) -> int | float:
    return int(value) if value == value.to_integral_value() else float(value)
