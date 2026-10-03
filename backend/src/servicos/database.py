"""Única camada de persistência; RLS também controla o acesso no banco."""

from src.clientes.schemas import Client, ClientCreate
from src.core.crypto import FieldCipher, mask
from src.core.supabase import Identity, SupabaseGateway
from src.produtos.schemas import Product, ProductCreate


class Database:
    def __init__(self, gateway: SupabaseGateway, identity: Identity, cipher: FieldCipher):
        self.gateway, self.identity, self.cipher = gateway, identity, cipher

    def _all(self, table: str, filters: dict | None = None) -> list[dict]:
        rows: list[dict] = []
        while True:
            page = self.gateway.request("GET", f"/rest/v1/{table}", params={"select": "*", "order": "id.asc", "limit": "500", "owner_id": f"eq.{self.identity.owner_id}", "id": f"gt.{rows[-1]['id'] if rows else 0}", **(filters or {})})
            if not page:
                return rows
            rows.extend(page)

    def list_products(self) -> list[Product]:
        return [Product.model_validate(row) for row in self._all("products")]

    def create_product(self, payload: ProductCreate) -> Product:
        data = payload.model_dump(mode="json")
        data["owner_id"] = self.identity.owner_id
        rows = self.gateway.request("POST", "/rest/v1/products", json=data, prefer="return=representation")
        return Product.model_validate(rows[0])

    def _client(self, row: dict) -> Client:
        owner = row["owner_id"]
        if owner != self.identity.owner_id:
            raise ValueError("Registro fora do escopo da sessão.")
        return Client(id=row["id"], name=row["name"], city=row["city"], **{
            field: self.cipher.decrypt(row[f"{field}_encrypted"], owner, field)
            for field in ("cpf", "email", "phone")
        })

    def list_clients(self, filters: dict | None = None) -> list[Client]:
        if self.identity.access_role == "support":
            return [Client.model_validate(row) for row in self._all("clients_support")]
        return [self._client(row) for row in self._all("clients", filters)]

    def create_client(self, payload: ClientCreate) -> Client:
        owner = self.identity.owner_id
        data = {"owner_id": owner, "name": payload.name, "city": payload.city}
        for field in ("cpf", "email", "phone"):
            value = str(getattr(payload, field))
            data[f"{field}_encrypted"] = self.cipher.encrypt(value, owner, field)
            data[f"{field}_masked"] = mask(value, field)
            if field != "phone":
                data[f"{field}_bindex"] = self.cipher.blind_index(value, owner, field)
        rows = self.gateway.request("POST", "/rest/v1/clients", json=data, prefer="return=representation")
        return self._client(rows[0])

    def remove(self, table: str, row_id: int) -> bool:
        if table not in {"clients", "products"}:
            raise ValueError("Tabela inválida.")
        return bool(self.gateway.request("DELETE", f"/rest/v1/{table}", params={"id": f"eq.{row_id}", "owner_id": f"eq.{self.identity.owner_id}"}, prefer="return=representation"))

    def dashboard(self) -> dict:
        return self.gateway.request("POST", "/rest/v1/rpc/dashboard_totals", json={"p_owner": self.identity.owner_id})
