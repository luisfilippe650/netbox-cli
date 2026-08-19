from pydantic import BaseModel, ConfigDict, Field


class AddSite(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1)
    slug: str | None = None
    status: str = "active"
    region: int | None = Field(default=None, gt=0)
    description: str = ""
