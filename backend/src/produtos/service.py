from src.produtos.schemas import Product, ProductCreate
from src.servicos.armazenamento import storage


def list_products() -> list[Product]:
    return storage.list_products()


def create_product(payload: ProductCreate) -> Product:
    return storage.create_product(payload)


def remove_product(product_id: int) -> bool:
    return storage.remove_product(product_id)
