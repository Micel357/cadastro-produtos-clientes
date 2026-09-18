from src.produtos.schemas import Product, ProductCreate
from src.servicos.memoria import memory_store


def list_products() -> list[Product]:
    return memory_store.products


def create_product(payload: ProductCreate) -> Product:
    product = Product(id=memory_store.next_product_id(), **payload.model_dump())
    memory_store.products.append(product)
    return product


def remove_product(product_id: int) -> bool:
    for product in memory_store.products:
        if product.id == product_id:
            memory_store.products.remove(product)
            return True
    return False
