from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from netbox_cli.schemas.identifiers import ResourceIdentifier


class AddDevice(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=64)
    role: ResourceIdentifier
    device_type: ResourceIdentifier
    site: ResourceIdentifier
    serial: str | None = Field(default=None, max_length=50)
    location: ResourceIdentifier | None = None
    rack: ResourceIdentifier | None = None
    position: Decimal | None = Field(default=None, ge=1, multiple_of=Decimal("0.5"))
    status: Literal["active"] = "active"
    custom_fields: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def rack_is_required_for_position(self) -> "AddDevice":
        if self.position is not None and self.rack is None:
            raise ValueError("rack é obrigatório quando position for informada")

        return self


class UpdateDevice(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=64)
    role: ResourceIdentifier | None = None
    device_type: ResourceIdentifier | None = None
    site: ResourceIdentifier | None = None
    serial: str | None = Field(default=None, max_length=50)
    status: str | None = None
    custom_fields: dict[str, Any] | None = None

    @model_validator(mode="after")
    def require_a_change(self) -> "UpdateDevice":
        if not any(value is not None for value in self.__dict__.values()):
            raise ValueError("informe ao menos um campo para atualizar")

        return self
