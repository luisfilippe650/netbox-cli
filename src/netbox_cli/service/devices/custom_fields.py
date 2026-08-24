from __future__ import annotations

from typing import Any

from netbox_cli.client import NetBoxClient, get_all_results
from netbox_cli.exceptions import NetBoxCLIError


class RequiredCustomFieldsError(NetBoxCLIError):
    """Campos personalizados obrigatórios não foram informados."""


class DeviceCustomFieldValidator:
    ENDPOINT = "/api/extras/custom-fields/"

    def __init__(self, client: NetBoxClient) -> None:
        self.client = client

    def validate(self, custom_fields: dict[str, Any]) -> None:
        definitions = get_all_results(
            self.client,
            self.ENDPOINT,
            params={"object_type": "dcim.device", "limit": 0},
        )
        missing = [
            _field_description(field)
            for field in definitions
            if _is_required_and_empty(field, custom_fields)
        ]

        if missing:
            raise RequiredCustomFieldsError(
                "Campos personalizados obrigatórios ausentes: " + ", ".join(missing)
            )


def _is_required_and_empty(
    field: dict[str, Any], custom_fields: dict[str, Any]
) -> bool:
    if not field.get("required"):
        return False

    name = str(field.get("name", ""))

    return name not in custom_fields or custom_fields[name] in (None, "", [])


def _field_description(field: dict[str, Any]) -> str:
    name = str(field.get("name", ""))
    label = str(field.get("label") or name)

    return f"{name} ({label})" if label != name else name
