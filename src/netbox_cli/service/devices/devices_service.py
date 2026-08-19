from __future__ import annotations

from typing import Any

from netbox_cli.exceptions import NetBoxCLIError
from netbox_cli.schemas.devices import AddDevice
from netbox_cli.service.base_service import CRUDService


class RequiredCustomFieldsError(NetBoxCLIError):
    """Campos personalizados obrigatórios não foram informados."""


class DevicesService(CRUDService[AddDevice]):
    ENDPOINT = "/api/dcim/devices/"
    CUSTOM_FIELDS_ENDPOINT = "/api/extras/custom-fields/"
    USES_SLUG = False

    def create(self, item: AddDevice) -> dict[str, Any]:
        self._validate_required_custom_fields(item.custom_fields)
        return self.client.post(self.ENDPOINT, self.build_payload(item))

    def build_payload(self, item: AddDevice) -> dict[str, Any]:
        payload = item.model_dump(mode="json", exclude_none=True)
        if item.position is not None:
            payload["face"] = "front"
        return payload

    def _validate_required_custom_fields(
        self, custom_fields: dict[str, Any]
    ) -> None:
        response = self.client.get(
            self.CUSTOM_FIELDS_ENDPOINT,
            params={"object_type": "dcim.device", "limit": 0},
        )
        definitions = response.get("results", []) if isinstance(response, dict) else []
        missing = []
        for field in definitions:
            if not isinstance(field, dict) or not field.get("required"):
                continue
            name = str(field.get("name", ""))
            value = custom_fields.get(name)
            if name not in custom_fields or value is None or value == "" or value == []:
                label = field.get("label") or name
                missing.append(f"{name} ({label})" if label != name else name)

        if missing:
            raise RequiredCustomFieldsError(
                "Campos personalizados obrigatórios ausentes: " + ", ".join(missing)
            )
