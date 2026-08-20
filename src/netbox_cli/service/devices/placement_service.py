from __future__ import annotations

from decimal import Decimal
from typing import Any

from netbox_cli.client import NetBoxClient
from netbox_cli.exceptions import NetBoxCLIError
from netbox_cli.service.devices.common import DEVICES_ENDPOINT, get_device, nested_value
from netbox_cli.service.lookup import get_scoped_rack


class DevicePlacementService:
    def __init__(self, client: NetBoxClient) -> None:
        self.client = client

    def move(
        self,
        name: str,
        *,
        rack_name: str,
        position: float,
        device_site_name: str | None = None,
        rack_site_name: str | None = None,
        rack_location_name: str | None = None,
    ) -> dict[str, Any]:
        _validate_position(position)
        device = get_device(self.client, name, site_name=device_site_name)
        return self._place(
            device,
            name=name,
            rack_name=rack_name,
            position=position,
            rack_site_name=rack_site_name,
            rack_location_name=rack_location_name,
        )

    def allocate(
        self,
        name: str,
        *,
        rack_name: str,
        position: float,
        device_site_name: str | None = None,
        rack_site_name: str | None = None,
        rack_location_name: str | None = None,
    ) -> dict[str, Any]:
        _validate_position(position)
        device = get_device(self.client, name, site_name=device_site_name)
        if device.get("rack") is not None:
            rack_label = nested_value(device["rack"], "name") or "rack desconhecido"
            raise NetBoxCLIError(
                f"Dispositivo '{name}' já está alocado em '{rack_label}'. "
                "Use 'netbox device move' para alterar sua posição."
            )
        result = self._place(
            device,
            name=name,
            rack_name=rack_name,
            position=position,
            rack_site_name=rack_site_name,
            rack_location_name=rack_location_name,
        )
        result["allocated"] = result.pop("moved")
        return result

    def deallocate(
        self, name: str, *, site_name: str | None = None
    ) -> dict[str, Any]:
        device = get_device(self.client, name, site_name=site_name)
        updated = self.client.patch(
            f"{DEVICES_ENDPOINT}{device['id']}/",
            {"rack": None, "position": None, "face": None},
        )
        return {
            "deallocated": True,
            "device": updated.get("name", name) if isinstance(updated, dict) else name,
            "previous_rack": nested_value(device.get("rack"), "name"),
            "previous_position": device.get("position"),
        }

    def _place(
        self,
        device: dict[str, Any],
        *,
        name: str,
        rack_name: str,
        position: float,
        rack_site_name: str | None,
        rack_location_name: str | None,
    ) -> dict[str, Any]:
        rack = get_scoped_rack(
            self.client,
            rack_name,
            site_name=rack_site_name,
            location_name=rack_location_name,
        )
        payload: dict[str, Any] = {
            "rack": rack["id"],
            "position": position,
            "face": "front",
        }
        rack_site = rack.get("site")
        if isinstance(rack_site, dict) and rack_site.get("id") is not None:
            payload["site"] = rack_site["id"]
        rack_location = rack.get("location")
        payload["location"] = (
            rack_location.get("id") if isinstance(rack_location, dict) else None
        )
        updated = self.client.patch(f"{DEVICES_ENDPOINT}{device['id']}/", payload)
        return {
            "moved": True,
            "device": updated.get("name", name) if isinstance(updated, dict) else name,
            "rack": rack.get("name", rack_name),
            "position": position,
            "face": "front",
        }


def _validate_position(position: float) -> None:
    if Decimal(str(position)) % Decimal("0.5"):
        raise NetBoxCLIError("--position deve ser múltiplo de 0.5.")
