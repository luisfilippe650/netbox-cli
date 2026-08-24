from pydantic import BaseModel, ConfigDict, Field, model_validator


class AddDeviceRole(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1)
    color: str = Field(default="9e9e9e", pattern=r"^[0-9a-fA-F]{6}$")
    vm_role: bool = True
    description: str = Field(default="", max_length=200)


class UpdateDeviceRole(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1)
    color: str | None = Field(default=None, pattern=r"^[0-9a-fA-F]{6}$")
    vm_role: bool | None = None
    description: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def require_a_change(self) -> "UpdateDeviceRole":
        if not any(value is not None for value in self.__dict__.values()):
            raise ValueError("informe ao menos um campo para atualizar")

        return self
