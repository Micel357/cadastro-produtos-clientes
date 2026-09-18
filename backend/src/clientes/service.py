from src.clientes.schemas import Client, ClientCreate
from src.servicos.armazenamento import storage


def list_clients() -> list[Client]:
    return storage.list_clients()


def create_client(payload: ClientCreate) -> Client:
    return storage.create_client(payload)


def remove_client(client_id: int) -> bool:
    return storage.remove_client(client_id)
