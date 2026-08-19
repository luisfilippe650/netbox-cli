from pydantic import BaseModel, ConfigDict, Field


class AddRackGroup(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1)


class UpdateRackGroup(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1)
