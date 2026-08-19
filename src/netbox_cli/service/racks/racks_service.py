from netbox_cli.exceptions import NetBoxCLIError
from netbox_cli.schemas.racks import AddRack
from netbox_cli.service.base_service import CRUDService
from netbox_cli.service.capacity import rack_capacity
from netbox_cli.service.lookup import get_result_list, get_scoped_rack


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
        response = self.client.get(
            f"{self.ENDPOINT}{rack['id']}/elevation/",
            params={"face": face, "limit": 0},
        )
        units = get_result_list(response)
        return {
            "id": rack.get("id"),
            "name": rack.get("name") or rack.get("display"),
            "site": _value(rack.get("site")),
            "location": _value(rack.get("location")),
            "face": face,
            "u_height": rack.get("u_height"),
            "starting_unit": rack.get("starting_unit", 1),
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
        if height < 0.5 or (height * 2) % 1:
            raise NetBoxCLIError("--height deve ser múltiplo de 0.5 e maior que zero.")

        elevation = self.elevation(
            name,
            face=face,
            site_name=site_name,
            location_name=location_name,
        )
        units = elevation["units"]
        occupied = {
            float(unit["id"])
            for unit in units
            if isinstance(unit, dict)
            and unit.get("occupied")
            and _is_number(unit.get("id"))
        }
        starting_unit = float(elevation.get("starting_unit") or 1)
        top_half_unit = starting_unit + float(elevation.get("u_height") or 0) - 0.5
        required_slots = int(height * 2)
        candidates = []
        position = starting_unit
        while position + height - 0.5 <= top_half_unit:
            slots = {position + offset * 0.5 for offset in range(required_slots)}
            if not slots.intersection(occupied):
                candidates.append(position)
            position += 0.5
        return {
            "rack": elevation["name"],
            "face": face,
            "height": height,
            "count": len(candidates),
            "positions": candidates,
        }


def _value(value: object) -> object:
    if isinstance(value, dict):
        return value.get("name") or value.get("display")
    return value


def _is_number(value: object) -> bool:
    try:
        float(str(value))
    except (TypeError, ValueError):
        return False
    return True
