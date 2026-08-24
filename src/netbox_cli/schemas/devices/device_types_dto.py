from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from netbox_cli.schemas.identifiers import ResourceIdentifier


class AddDeviceType(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    manufacturer: ResourceIdentifier
    model: str = Field(min_length=1)
    u_height: Decimal = Field(ge=0, max_digits=4, decimal_places=1)


class UpdateDeviceType(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    manufacturer: ResourceIdentifier | None = None
    model: str | None = Field(default=None, min_length=1)
    u_height: Decimal | None = Field(default=None, ge=0, max_digits=4, decimal_places=1)

    @model_validator(mode="after")
    def require_a_change(self) -> "UpdateDeviceType":
        if not any(value is not None for value in self.__dict__.values()):
            raise ValueError("informe ao menos um campo para atualizar")

        return self
