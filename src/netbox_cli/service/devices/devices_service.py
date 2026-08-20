from __future__ import annotations

from typing import Any

from netbox_cli.client import NetBoxClient
from netbox_cli.schemas.devices import AddDevice
from netbox_cli.service.base_service import CRUDService
from netbox_cli.service.devices.common import DEVICES_ENDPOINT
from netbox_cli.service.devices.custom_fields import (
    DeviceCustomFieldValidator,
    RequiredCustomFieldsError,
)
from netbox_cli.service.devices.inspection_service import DeviceInspectionService
from netbox_cli.service.devices.placement_service import DevicePlacementService
from netbox_cli.service.devices.trace_service import CableTraceService


class DevicesService(CRUDService[AddDevice]):
    """Fachada estável para as operações de dispositivo expostas pela CLI."""

    ENDPOINT = DEVICES_ENDPOINT
    USES_SLUG = False

    def __init__(
        self,
        client: NetBoxClient,
        *,
        inspection: DeviceInspectionService | None = None,
        placement: DevicePlacementService | None = None,
        cable_trace: CableTraceService | None = None,
        custom_fields: DeviceCustomFieldValidator | None = None,
    ) -> None:
        super().__init__(client)
        self.inspection = inspection or DeviceInspectionService(client)
        self.placement = placement or DevicePlacementService(client)
        self.cable_trace = cable_trace or CableTraceService(client)
        self.custom_fields = custom_fields or DeviceCustomFieldValidator(client)

    def create(self, item: AddDevice) -> dict[str, Any]:
        self.custom_fields.validate(item.custom_fields)
        return super().create(item)

    def ensure(
        self,
        item: AddDevice,
        *,
        identity_field: str = "name",
        filters: dict[str, Any] | None = None,
        update_fields: set[str] | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        if update_fields is None:
            update_fields = set(item.model_fields_set)
            if "position" in update_fields and item.position is not None:
                update_fields.add("face")
        if "custom_fields" in update_fields:
            self.custom_fields.validate(item.custom_fields)
        return super().ensure(
            item,
            identity_field=identity_field,
            filters=filters,
            update_fields=update_fields,
            dry_run=dry_run,
        )

    def build_payload(self, item: AddDevice) -> dict[str, Any]:
        payload = item.model_dump(mode="json", exclude_none=True)
        if item.position is not None:
            payload["face"] = "front"
        return payload

    def inspect(self, name: str, *, site_name: str | None = None) -> dict[str, Any]:
        return self.inspection.inspect(name, site_name=site_name)

    def move(
        self,
        name: str,
        *,
        rack_name: str,
        position: float,
        device_site_name: str | None = None,
        rack_site_name: str | None = None,
        rack_location_name: str | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        return self.placement.move(
            name,
            rack_name=rack_name,
            position=position,
            device_site_name=device_site_name,
            rack_site_name=rack_site_name,
            rack_location_name=rack_location_name,
            dry_run=dry_run,
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
        dry_run: bool = False,
    ) -> dict[str, Any]:
        return self.placement.allocate(
            name,
            rack_name=rack_name,
            position=position,
            device_site_name=device_site_name,
            rack_site_name=rack_site_name,
            rack_location_name=rack_location_name,
            dry_run=dry_run,
        )

    def deallocate(
        self,
        name: str,
        *,
        site_name: str | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        return self.placement.deallocate(
            name,
            site_name=site_name,
            dry_run=dry_run,
        )

    def trace(
        self,
        name: str,
        interface_name: str,
        *,
        site_name: str | None = None,
    ) -> dict[str, Any]:
        return self.cable_trace.trace(name, interface_name, site_name=site_name)


__all__ = ["DevicesService", "RequiredCustomFieldsError"]
