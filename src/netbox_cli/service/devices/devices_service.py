from __future__ import annotations

from typing import Any

from netbox_cli.client import NetBoxClient
from netbox_cli.schemas.devices import AddDevice, UpdateDevice
from netbox_cli.service.base_service import CRUDService
from netbox_cli.service.devices.common import DEVICES_ENDPOINT
from netbox_cli.service.devices.custom_fields import (
    DeviceCustomFieldValidator,
    RequiredCustomFieldsError,
)
from netbox_cli.service.devices.device_roles_service import DeviceRolesService
from netbox_cli.service.devices.inspection_service import DeviceInspectionService
from netbox_cli.service.devices.placement_service import DevicePlacementService
from netbox_cli.service.devices.trace_service import CableTraceService
from netbox_cli.service.lookup import resolve_resource_id


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
        self.device_roles = DeviceRolesService(client)
        self._relationship_ids: dict[tuple[str, str, tuple[tuple[str, Any], ...]], int] = {}

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

        site_id = self._resolve_relationship(
            "/api/dcim/sites/",
            item.site,
            resource_label="Site",
        )

        return super().ensure(
            item,
            identity_field=identity_field,
            filters={**(filters or {}), "site_id": site_id},
            update_fields=update_fields,
            dry_run=dry_run,
        )

    def build_payload(self, item: AddDevice | UpdateDevice) -> dict[str, Any]:
        payload = item.model_dump(mode="json", exclude_none=True)
        if item.role is not None:
            payload["role"] = self.device_roles.resolve_id(item.role)

        site_id: int | None = None

        if item.site is not None:
            site_id = self._resolve_relationship(
                "/api/dcim/sites/",
                item.site,
                resource_label="Site",
            )
            payload["site"] = site_id

        if item.device_type is not None:
            payload["device_type"] = self._resolve_relationship(
                "/api/dcim/device-types/",
                item.device_type,
                resource_label="Tipo de dispositivo",
                fields=("model", "slug"),
            )

        if isinstance(item, UpdateDevice):
            if item.custom_fields is not None:
                self.custom_fields.validate(item.custom_fields)

            return payload

        location_id: int | None = None

        if item.location is not None:
            location_id = self._resolve_relationship(
                "/api/dcim/locations/",
                item.location,
                resource_label="Localização",
                filters={"site_id": site_id},
            )
            payload["location"] = location_id

        if item.rack is not None:
            filters = {"site_id": site_id}

            if location_id is not None:
                filters["location_id"] = location_id

            payload["rack"] = self._resolve_relationship(
                "/api/dcim/racks/",
                item.rack,
                resource_label="Rack",
                filters=filters,
            )

        if item.position is not None:
            payload["position"] = float(item.position)
            payload["face"] = "front"

        return payload

    def _resolve_relationship(
        self,
        endpoint: str,
        identifier: int | str,
        *,
        resource_label: str,
        fields: tuple[str, ...] = ("name", "slug"),
        filters: dict[str, Any] | None = None,
    ) -> int:
        if isinstance(identifier, int):
            return identifier

        filter_items = tuple(sorted((filters or {}).items()))
        cache_key = (endpoint, identifier.casefold(), filter_items)

        if cache_key not in self._relationship_ids:
            self._relationship_ids[cache_key] = resolve_resource_id(
                self.client,
                endpoint,
                identifier,
                resource_label=resource_label,
                fields=fields,
                filters=filters,
            )

        return self._relationship_ids[cache_key]

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
