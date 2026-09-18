"""Armazenamento compartilhado em JSON para a versão acadêmica do projeto."""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from src.clientes.schemas import Client, ClientCreate
from src.core.config import settings
from src.produtos.schemas import Product, ProductCreate


INITIAL_STATE = {
    "products": [
        {"id": 1, "name": "Caderno pontilhado", "category": "Papelaria", "price": 29.90, "stock": 18, "description": "Capa dura, 96 folhas."},
        {"id": 2, "name": "Caneta gel azul", "category": "Escrita", "price": 7.50, "stock": 42, "description": "Tinta de secagem rápida."},
    ],
    "clients": [
        {"id": 1, "name": "Ana Martins", "email": "ana@example.com", "phone": "(85) 99999-1111", "city": "Fortaleza"},
        {"id": 2, "name": "Bruno Lima", "email": "bruno@example.com", "phone": "(85) 98888-2222", "city": "Caucaia"},
    ],
}


class JsonStore:
    """Lê e grava o mesmo arquivo JSON com bloqueio exclusivo durante alterações."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.lock_path = self.path.with_suffix(f"{self.path.suffix}.lock")

    @contextmanager
    def _locked(self) -> Iterator[None]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.lock_path.open("a+") as lock_file:
            if os.name == "posix":
                import fcntl
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                if os.name == "posix":
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def _read(self) -> dict[str, list[dict[str, object]]]:
        if not self.path.exists():
            return {"products": [], "clients": []}
        with self.path.open(encoding="utf-8") as file:
            return json.load(file)

    def _write(self, state: dict[str, list[dict[str, object]]]) -> None:
        temporary_path = self.path.with_suffix(f"{self.path.suffix}.tmp")
        with temporary_path.open("w", encoding="utf-8") as file:
            json.dump(state, file, ensure_ascii=False, indent=2)
        temporary_path.replace(self.path)

    def initialize(self) -> None:
        with self._locked():
            if not self.path.exists():
                self._write(INITIAL_STATE)

    def reset(self) -> None:
        with self._locked():
            if self.path.exists():
                self.path.unlink()

    def snapshot(self) -> dict[str, list[dict[str, object]]]:
        with self._locked():
            return self._read()

    def list_products(self) -> list[Product]:
        return [Product.model_validate(product) for product in self.snapshot()["products"]]

    def create_product(self, payload: ProductCreate) -> Product:
        with self._locked():
            state = self._read()
            product_id = max((int(product["id"]) for product in state["products"]), default=0) + 1
            product = Product(id=product_id, **payload.model_dump())
            state["products"].append(product.model_dump())
            self._write(state)
            return product

    def remove_product(self, product_id: int) -> bool:
        with self._locked():
            state = self._read()
            products = state["products"]
            remaining = [product for product in products if int(product["id"]) != product_id]
            if len(remaining) == len(products):
                return False
            state["products"] = remaining
            self._write(state)
            return True

    def list_clients(self) -> list[Client]:
        return [Client.model_validate(client) for client in self.snapshot()["clients"]]

    def create_client(self, payload: ClientCreate) -> Client:
        with self._locked():
            state = self._read()
            client_id = max((int(client["id"]) for client in state["clients"]), default=0) + 1
            client = Client(id=client_id, **payload.model_dump())
            state["clients"].append(client.model_dump(mode="json"))
            self._write(state)
            return client

    def remove_client(self, client_id: int) -> bool:
        with self._locked():
            state = self._read()
            clients = state["clients"]
            remaining = [client for client in clients if int(client["id"]) != client_id]
            if len(remaining) == len(clients):
                return False
            state["clients"] = remaining
            self._write(state)
            return True


storage = JsonStore(settings.data_file)
