from pydantic import BaseModel, ConfigDict, Field


class AddLocation(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1)
    site: int = Field(gt=0)
    slug: str | None = None
    status: str = "active"
    parent: int | None = Field(default=None, gt=0)
    description: str = ""
