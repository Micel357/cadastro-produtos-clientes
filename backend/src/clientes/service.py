from src.clientes.schemas import Client, ClientCreate
from src.servicos.memoria import memory_store


def list_clients() -> list[Client]:
    return memory_store.clients


def create_client(payload: ClientCreate) -> Client:
    client = Client(id=memory_store.next_client_id(), **payload.model_dump())
    memory_store.clients.append(client)
    return client


def remove_client(client_id: int) -> bool:
    for client in memory_store.clients:
        if client.id == client_id:
            memory_store.clients.remove(client)
            return True
    return False
