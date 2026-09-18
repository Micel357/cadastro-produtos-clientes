from pydantic import BaseModel, Field


class ProductCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    category: str = Field(min_length=2, max_length=50)
    price: float = Field(gt=0)
    stock: int = Field(ge=0)
    description: str = Field(default="", max_length=180)


class Product(ProductCreate):
    id: int
