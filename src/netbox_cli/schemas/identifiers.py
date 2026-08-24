from typing import Annotated

from pydantic import BeforeValidator


def normalize_resource_identifier(value: object) -> int | str:
    """Normaliza IDs numéricos e preserva nomes ou slugs não vazios."""
    if isinstance(value, int):
        if value <= 0:
            raise ValueError("o identificador deve ser um ID positivo, nome ou slug")

        return value

    if not isinstance(value, str):
        raise ValueError("o identificador deve ser um ID positivo, nome ou slug")

    normalized = value.strip()
    is_integer = normalized.lstrip("+-").isdecimal()

    if not normalized or (is_integer and int(normalized) <= 0):
        raise ValueError("o identificador deve ser um ID positivo, nome ou slug")

    return int(normalized) if normalized.isdecimal() else normalized


ResourceIdentifier = Annotated[
    int | str,
    BeforeValidator(normalize_resource_identifier),
]
