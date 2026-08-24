from typing import Any

from netbox_cli.client import NetBoxClient
from netbox_cli.exceptions import NetBoxCLIError
from netbox_cli.schemas.organization.locations_dto import AddLocation, UpdateLocation
from netbox_cli.service.base_service import CRUDService
from netbox_cli.service.lookup import resolve_resource_id


class LocationsService(CRUDService[AddLocation]):
    ENDPOINT = "/api/dcim/locations/"

    def __init__(self, client: NetBoxClient) -> None:
        super().__init__(client)
        self._site_ids: dict[str, int] = {}
        self._parent_ids: dict[tuple[int, str], int] = {}

    def build_payload(self, item: AddLocation | UpdateLocation) -> dict[str, Any]:
        payload = super().build_payload(item)
        site_id = self.resolve_site_id(item.site) if item.site is not None else None

        if site_id is not None:
            payload["site"] = site_id

        if isinstance(item.parent, str):
            if site_id is None:
                raise NetBoxCLIError(
                    "site é necessário para resolver o local pai pelo nome"
                )

            cache_key = (site_id, item.parent.casefold())

            if cache_key not in self._parent_ids:
                self._parent_ids[cache_key] = resolve_resource_id(
                    self.client,
                    self.ENDPOINT,
                    item.parent,
                    resource_label="Local pai",
                    filters={"site_id": site_id},
                )

            payload["parent"] = self._parent_ids[cache_key]

        return payload

    def resolve_site_id(self, identifier: int | str) -> int:
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

    def ensure(
        self,
        item: AddLocation,
        *,
        identity_field: str = "name",
        filters: dict[str, Any] | None = None,
        update_fields: set[str] | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        site_id = self.resolve_site_id(item.site)

        return super().ensure(
            item,
            identity_field=identity_field,
            filters={**(filters or {}), "site_id": site_id},
            update_fields=update_fields,
            dry_run=dry_run,
        )
