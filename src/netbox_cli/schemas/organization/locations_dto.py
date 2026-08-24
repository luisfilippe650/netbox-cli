from pydantic import BaseModel, ConfigDict, Field, model_validator

from netbox_cli.schemas.identifiers import ResourceIdentifier


class AddLocation(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1)
    site: ResourceIdentifier
    slug: str | None = None
    status: str = "active"
    parent: ResourceIdentifier | None = None
    description: str = ""


class UpdateLocation(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1)
    site: ResourceIdentifier | None = None
    slug: str | None = None
    status: str | None = None
    parent: ResourceIdentifier | None = None
    description: str | None = None

    @model_validator(mode="after")
    def require_a_change(self) -> "UpdateLocation":
        if not any(value is not None for value in self.__dict__.values()):
            raise ValueError("informe ao menos um campo para atualizar")

        return self
