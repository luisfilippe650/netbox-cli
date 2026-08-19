from __future__ import annotations

import re
import unicodedata
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

from netbox_cli.client.netbox_client import NetBoxClient

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
        payload = item.model_dump(exclude_none=True)
        if self.USES_SLUG and "name" in payload:
            payload["slug"] = payload.get("slug") or slugify(payload["name"])
        return payload

    def create(self, item: CreateModel) -> dict[str, Any]:
        return self.client.post(self.ENDPOINT, self.build_payload(item))

    def list(
        self, *, search: str | None = None, limit: int | None = None
    ) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if search:
            params["q"] = search
        if limit is not None:
            params["limit"] = limit
        return self.client.get(self.ENDPOINT, params=params or None)

    def get(self, item_id: int) -> dict[str, Any]:
        return self.client.get(f"{self.ENDPOINT}{item_id}/")

    def update(self, item_id: int, item: BaseModel) -> dict[str, Any]:
        return self.client.patch(f"{self.ENDPOINT}{item_id}/", self.build_payload(item))

    def delete(self, item_id: int) -> None:
        self.client.delete(f"{self.ENDPOINT}{item_id}/")
