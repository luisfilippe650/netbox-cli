from typing import Any

from netbox_cli.client import NetBoxClient
from netbox_cli.schemas.devices import AddDeviceType, UpdateDeviceType
from netbox_cli.service.base_service import CRUDService, slugify
from netbox_cli.service.lookup import resolve_resource_id


class DeviceTypesService(CRUDService[AddDeviceType]):
    ENDPOINT = "/api/dcim/device-types/"
    MANUFACTURERS_ENDPOINT = "/api/dcim/manufacturers/"
    USES_SLUG = False

    def __init__(self, client: NetBoxClient) -> None:
        super().__init__(client)
        self._manufacturer_ids: dict[str, int] = {}

    def build_payload(self, item: AddDeviceType | UpdateDeviceType) -> dict[str, Any]:
        payload = item.model_dump(mode="json", exclude_none=True)

        if item.manufacturer is not None:
            payload["manufacturer"] = self.resolve_manufacturer_id(item.manufacturer)

        if item.model is not None:
            payload["slug"] = slugify(item.model)

        return payload

    def resolve_manufacturer_id(self, identifier: int | str) -> int:
        if isinstance(identifier, int):
            return identifier

        cache_key = identifier.casefold()

        if cache_key not in self._manufacturer_ids:
            self._manufacturer_ids[cache_key] = resolve_resource_id(
                self.client,
                self.MANUFACTURERS_ENDPOINT,
                identifier,
                resource_label="Fabricante",
            )

        return self._manufacturer_ids[cache_key]

    def ensure(
        self,
        item: AddDeviceType,
        *,
        identity_field: str = "model",
        filters: dict[str, Any] | None = None,
        update_fields: set[str] | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        manufacturer_id = self.resolve_manufacturer_id(item.manufacturer)

        return super().ensure(
            item,
            identity_field=identity_field,
            filters={**(filters or {}), "manufacturer_id": manufacturer_id},
            update_fields=update_fields,
            dry_run=dry_run,
        )
