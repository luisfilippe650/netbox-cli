from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

RackWidth = Literal[10, 19, 21, 23]


class AddRack(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    site: int = Field(gt=0)
    name: str = Field(min_length=1)
    width: RackWidth
    starting_unit: int = Field(gt=0)
    u_height: int = Field(gt=0)
    status: Literal["active"] = "active"
    location: int | None = Field(default=None, gt=0)
    group: int | None = Field(default=None, gt=0)
    role: int | None = Field(default=None, gt=0)
    rack_type: int | None = Field(default=None, gt=0)


class UpdateRack(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    site: int | None = Field(default=None, gt=0)
    name: str | None = Field(default=None, min_length=1)
    width: RackWidth | None = None
    starting_unit: int | None = Field(default=None, gt=0)
    u_height: int | None = Field(default=None, gt=0)
    location: int | None = Field(default=None, gt=0)
    group: int | None = Field(default=None, gt=0)
    role: int | None = Field(default=None, gt=0)
    rack_type: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def require_a_change(self) -> "UpdateRack":
        if not any(value is not None for value in self.__dict__.values()):
            raise ValueError("informe ao menos um campo para atualizar")
        return self
