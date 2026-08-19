from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class AddDeviceType(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    manufacturer: int = Field(gt=0)
    model: str = Field(min_length=1)
    u_height: Decimal = Field(ge=0, max_digits=4, decimal_places=1)
