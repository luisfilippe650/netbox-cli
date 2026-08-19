from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AddDevice(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=64)
    role: int = Field(gt=0)
    device_type: int = Field(gt=0)
    site: int = Field(gt=0)
    serial: str | None = Field(default=None, max_length=50)
    location: int | None = Field(default=None, gt=0)
    rack: int | None = Field(default=None, gt=0)
    position: Decimal | None = Field(default=None, ge=1, multiple_of=Decimal("0.5"))
    status: Literal["active"] = "active"
    custom_fields: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def rack_is_required_for_position(self) -> "AddDevice":
        if self.position is not None and self.rack is None:
            raise ValueError("rack é obrigatório quando position for informada")
        return self
