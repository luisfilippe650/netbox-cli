from __future__ import annotations

import re
import unicodedata
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

from netbox_cli.client.netbox_client import NetBoxClient
from netbox_cli.client.pagination import get_all_results
from netbox_cli.exceptions import NetBoxCLIError

CreateModel = TypeVar("CreateModel", bound=BaseModel)


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()

    return re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")


class CRUDService(Generic[CreateModel]):
    ENDPOINT = ""
    USES_SLUG = True

    def __init__(self, client: NetBoxClient) -> None:
        self.client = client

    def build_payload(self, item: CreateModel) -> dict[str, Any]:
        payload = item.model_dump(mode="json", exclude_none=True)

        if self.USES_SLUG and "name" in payload:
            payload["slug"] = payload.get("slug") or slugify(payload["name"])

        return payload

    def create(self, item: CreateModel) -> dict[str, Any]:
        return self.client.post(self.ENDPOINT, self.build_payload(item))

    def ensure(
        self,
        item: CreateModel,
        *,
        identity_field: str = "name",
        filters: dict[str, Any] | None = None,
        update_fields: set[str] | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Cria ou converge um recurso identificado de forma única."""
        payload = self.build_payload(item)
        identity = payload[identity_field]
        params = {**(filters or {}), identity_field: identity, "limit": 0}
        candidates = get_all_results(self.client, self.ENDPOINT, params=params)
        matches = [
            candidate
            for candidate in candidates
            if str(candidate.get(identity_field, "")).casefold()
            == str(identity).casefold()
        ]

        if len(matches) > 1:
            raise NetBoxCLIError(
                f"Mais de um recurso corresponde a {identity_field}={identity!r}."
            )

        if not matches:
            if dry_run:
                return {
                    "action": "would_create",
                    "changed": True,
                    "dry_run": True,
                    "payload": payload,
                }

            created = self.create(item)

            return {"action": "created", "changed": True, "resource": created}

        current = matches[0]
        selected_fields = (
            set(item.model_fields_set) if update_fields is None else update_fields
        )
        comparable_payload = {
            field: payload[field] for field in selected_fields if field in payload
        }
        changes = {
            field: desired
            for field, desired in comparable_payload.items()
            if not _same_api_value(current.get(field), desired)
        }

        if not changes:
            return {
                "action": "unchanged",
                "changed": False,
                "resource": current,
            }

        if dry_run:
            return {
                "action": "would_update",
                "changed": True,
                "dry_run": True,
                "id": current.get("id"),
                "changes": changes,
                "resource": current,
            }

        updated = self.client.patch(
            f"{self.ENDPOINT}{current['id']}/",
            changes,
        )

        return {
            "action": "updated",
            "changed": True,
            "changes": changes,
            "resource": updated,
        }

    def list(
        self, *, search: str | None = None, limit: int | None = None
    ) -> dict[str, Any]:
        params: dict[str, Any] = {}

        if search:
            params["q"] = search

        if limit is not None:
            params["limit"] = limit

        if limit == 0:
            results = get_all_results(self.client, self.ENDPOINT, params=params)

            return {
                "count": len(results),
                "next": None,
                "previous": None,
                "results": results,
            }

        return self.client.get(self.ENDPOINT, params=params or None)

    def get(self, item_id: int) -> dict[str, Any]:
        return self.client.get(f"{self.ENDPOINT}{item_id}/")

    def update(self, item_id: int, item: BaseModel) -> dict[str, Any]:
        return self.client.patch(f"{self.ENDPOINT}{item_id}/", self.build_payload(item))

    def changes_for(self, current: dict[str, Any], item: BaseModel) -> dict[str, Any]:
        payload = self.build_payload(item)

        return {
            field: desired
            for field, desired in payload.items()
            if not _same_api_value(current.get(field), desired)
        }

    def delete(self, item_id: int) -> None:
        self.client.delete(f"{self.ENDPOINT}{item_id}/")


def _same_api_value(current: Any, desired: Any) -> bool:
    if isinstance(current, dict) and not isinstance(desired, dict):
        for key in ("id", "value", "name", "slug"):
            if key in current and _same_api_value(current[key], desired):
                return True

        return False

    if isinstance(current, (int, float)) and isinstance(desired, (int, float)):
        return float(current) == float(desired)

    if isinstance(current, (int, float)) and isinstance(desired, str):
        try:
            return float(current) == float(desired)
        except ValueError:
            return False

    return current == desired
