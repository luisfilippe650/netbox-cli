from netbox_cli.client import NetBoxClient
from netbox_cli.schemas.devices import AddDeviceRole
from netbox_cli.service.base_service import CRUDService
from netbox_cli.service.lookup import resolve_resource_id


class DeviceRolesService(CRUDService[AddDeviceRole]):
    ENDPOINT = "/api/dcim/device-roles/"

    def __init__(self, client: NetBoxClient) -> None:
        super().__init__(client)
        self._resolved_ids: dict[str, int] = {}

    def resolve_id(self, identifier: int | str) -> int:
        """Resolve um ID ou o nome exato de uma função de dispositivo."""
        if isinstance(identifier, int):
            return identifier

        normalized = identifier.strip()

        if normalized.isdecimal():
            role_id = int(normalized)

            if role_id > 0:
                return role_id

        cache_key = normalized.casefold()

        if cache_key in self._resolved_ids:
            return self._resolved_ids[cache_key]

        role_id = resolve_resource_id(
            self.client,
            self.ENDPOINT,
            normalized,
            resource_label="Função de dispositivo",
        )
        self._resolved_ids[cache_key] = role_id

        return role_id
