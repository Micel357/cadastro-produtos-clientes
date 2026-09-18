from src.produtos.schemas import ProductCreate
from src.produtos.service import create_product, list_products, remove_product


def test_cria_e_remove_produto() -> None:
    product = create_product(ProductCreate(name="Marca texto", category="Escrita", price=5.5, stock=3))

    assert product in list_products()
    assert remove_product(product.id) is True
    assert remove_product(product.id) is False
