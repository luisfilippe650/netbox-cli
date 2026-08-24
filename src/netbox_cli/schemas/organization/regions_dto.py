from pydantic import BaseModel, ConfigDict, Field, model_validator


class AddRegion(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1)
    slug: str | None = None
    description: str = ""


class UpdateRegion(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1)
    slug: str | None = None
    description: str | None = None

    @model_validator(mode="after")
    def require_a_change(self) -> "UpdateRegion":
        if not any(value is not None for value in self.__dict__.values()):
            raise ValueError("informe ao menos um campo para atualizar")

        return self


# Compatibilidade com o nome usado na primeira versão do projeto.
AddRegions = AddRegion
