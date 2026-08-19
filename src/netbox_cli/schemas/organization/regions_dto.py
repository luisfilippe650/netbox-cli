from pydantic import BaseModel, ConfigDict, Field


class AddRegion(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1)
    slug: str | None = None
    description: str = ""


# Compatibilidade com o nome usado na primeira versão do projeto.
AddRegions = AddRegion
