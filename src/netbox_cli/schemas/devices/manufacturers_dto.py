from pydantic import BaseModel, ConfigDict, Field


class AddManufacturer(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1)
    comments: str | None = None
