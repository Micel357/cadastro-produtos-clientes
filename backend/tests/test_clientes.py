from src.clientes.schemas import ClientCreate
from src.clientes.service import create_client, list_clients, remove_client


def test_cria_e_remove_cliente() -> None:
    client = create_client(ClientCreate(name="Carla Souza", email="carla@example.com", phone="85999990000", city="Fortaleza", cpf="123.456.789-01"))

    assert client in list_clients()
    assert client.cpf == "12345678901"
    assert remove_client(client.id) is True
    assert remove_client(client.id) is False
