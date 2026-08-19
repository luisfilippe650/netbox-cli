from typing import Any

from netbox_cli.schemas.devices import AddDeviceType
from netbox_cli.service.base_service import CRUDService, slugify


class DeviceTypesService(CRUDService[AddDeviceType]):
    ENDPOINT = "/api/dcim/device-types/"
    USES_SLUG = False

    def build_payload(self, item: AddDeviceType) -> dict[str, Any]:
        payload = item.model_dump(mode="json")
        payload["slug"] = slugify(item.model)
        return payload
