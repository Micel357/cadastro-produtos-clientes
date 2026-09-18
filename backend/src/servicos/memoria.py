from dataclasses import dataclass, field

from src.clientes.schemas import Client
from src.produtos.schemas import Product


@dataclass
class MemoryStore:
    products: list[Product] = field(default_factory=lambda: [
        Product(id=1, name="Caderno pontilhado", category="Papelaria", price=29.90, stock=18, description="Capa dura, 96 folhas."),
        Product(id=2, name="Caneta gel azul", category="Escrita", price=7.50, stock=42, description="Tinta de secagem rápida."),
    ])
    clients: list[Client] = field(default_factory=lambda: [
        Client(id=1, name="Ana Martins", email="ana@example.com", phone="(85) 99999-1111", city="Fortaleza"),
        Client(id=2, name="Bruno Lima", email="bruno@example.com", phone="(85) 98888-2222", city="Caucaia"),
    ])

    def next_product_id(self) -> int:
        return max((product.id for product in self.products), default=0) + 1

    def next_client_id(self) -> int:
        return max((client.id for client in self.clients), default=0) + 1


memory_store = MemoryStore()
