from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class ProductCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=2, max_length=80)
    category: str = Field(min_length=2, max_length=50)
    price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    stock: int = Field(ge=0, le=2147483647)
    description: str = Field(default="", max_length=180)

    @field_serializer("price")
    def serialize_price(self, value: Decimal) -> float:
        return float(value)


class Product(ProductCreate):
    id: int
