from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from netbox_cli.schemas.identifiers import ResourceIdentifier
TerminationType = Literal[
    "interface",
    "front-port",
    "rear-port",
    "console-port",
    "power-port",
]


class ConnectivityModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class UpdateModel(ConnectivityModel):
    @model_validator(mode="after")
    def require_a_change(self) -> "UpdateModel":
        if not any(value is not None for value in self.__dict__.values()):
            raise ValueError("informe ao menos um campo para atualizar")

        return self


class AddInterface(ConnectivityModel):
    device: ResourceIdentifier
    name: str = Field(min_length=1, max_length=64)
    type: str = Field(min_length=1)
    label: str = ""
    enabled: bool = True
    mtu: int | None = Field(default=None, gt=0)
    mgmt_only: bool = False
    description: str = Field(default="", max_length=200)


class UpdateInterface(UpdateModel):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    type: str | None = Field(default=None, min_length=1)
    label: str | None = None
    enabled: bool | None = None
    mtu: int | None = Field(default=None, gt=0)
    mgmt_only: bool | None = None
    description: str | None = Field(default=None, max_length=200)


class AddRearPort(ConnectivityModel):
    device: ResourceIdentifier
    name: str = Field(min_length=1, max_length=64)
    type: str = Field(min_length=1)
    positions: int = Field(default=1, gt=0)
    color: str = Field(default="", pattern=r"^$|^[0-9a-fA-F]{6}$")
    description: str = Field(default="", max_length=200)


class UpdateRearPort(UpdateModel):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    type: str | None = Field(default=None, min_length=1)
    positions: int | None = Field(default=None, gt=0)
    color: str | None = Field(default=None, pattern=r"^$|^[0-9a-fA-F]{6}$")
    description: str | None = Field(default=None, max_length=200)


class AddFrontPort(ConnectivityModel):
    device: ResourceIdentifier
    name: str = Field(min_length=1, max_length=64)
    type: str = Field(min_length=1)
    rear_port: ResourceIdentifier | None = None
    rear_port_position: int = Field(default=1, gt=0)
    color: str = Field(default="", pattern=r"^$|^[0-9a-fA-F]{6}$")
    description: str = Field(default="", max_length=200)


class UpdateFrontPort(UpdateModel):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    type: str | None = Field(default=None, min_length=1)
    color: str | None = Field(default=None, pattern=r"^$|^[0-9a-fA-F]{6}$")
    description: str | None = Field(default=None, max_length=200)


class AddConsolePort(ConnectivityModel):
    device: ResourceIdentifier
    name: str = Field(min_length=1, max_length=64)
    type: str | None = Field(default=None, min_length=1)
    speed: int | None = Field(default=None, gt=0)
    description: str = Field(default="", max_length=200)


class UpdateConsolePort(UpdateModel):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    type: str | None = Field(default=None, min_length=1)
    speed: int | None = Field(default=None, gt=0)
    description: str | None = Field(default=None, max_length=200)


class AddPowerPort(ConnectivityModel):
    device: ResourceIdentifier
    name: str = Field(min_length=1, max_length=64)
    type: str | None = Field(default=None, min_length=1)
    maximum_draw: int | None = Field(default=None, ge=0)
    allocated_draw: int | None = Field(default=None, ge=0)
    description: str = Field(default="", max_length=200)


class UpdatePowerPort(UpdateModel):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    type: str | None = Field(default=None, min_length=1)
    maximum_draw: int | None = Field(default=None, ge=0)
    allocated_draw: int | None = Field(default=None, ge=0)
    description: str | None = Field(default=None, max_length=200)


class AddCable(ConnectivityModel):
    a_type: TerminationType
    a_device: ResourceIdentifier
    a_name: str = Field(min_length=1)
    b_type: TerminationType
    b_device: ResourceIdentifier
    b_name: str = Field(min_length=1)
    type: str | None = Field(default=None, min_length=1)
    status: str = Field(default="connected", min_length=1)
    label: str = ""
    color: str = Field(default="", pattern=r"^$|^[0-9a-fA-F]{6}$")
    length: float | None = Field(default=None, gt=0)
    length_unit: str | None = Field(default=None, min_length=1)
    description: str = Field(default="", max_length=200)


class UpdateCable(UpdateModel):
    type: str | None = Field(default=None, min_length=1)
    status: str | None = Field(default=None, min_length=1)
    label: str | None = None
    color: str | None = Field(default=None, pattern=r"^$|^[0-9a-fA-F]{6}$")
    length: float | None = Field(default=None, gt=0)
    length_unit: str | None = Field(default=None, min_length=1)
    description: str | None = Field(default=None, max_length=200)
