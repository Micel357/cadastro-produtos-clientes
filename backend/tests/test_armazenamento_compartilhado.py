from src.produtos.schemas import ProductCreate
from src.servicos.armazenamento import JsonStore, storage


def test_two_store_instances_see_the_same_shared_file(tmp_path) -> None:
    shared_file = tmp_path / "cadastro.json"
    first_instance = JsonStore(shared_file)
    second_instance = JsonStore(shared_file)
    first_instance.initialize()

    created = first_instance.create_product(ProductCreate(name="Régua", category="Papelaria", price=4.5, stock=8))

    assert any(product.id == created.id for product in second_instance.list_products())


def test_default_store_uses_json_instead_of_in_memory_data() -> None:
    created = storage.create_product(ProductCreate(name="Lápis", category="Escrita", price=2.5, stock=12))

    assert any(product.id == created.id for product in storage.list_products())
