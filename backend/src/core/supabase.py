"""Cliente HTTP: sempre repassa o JWT do usuário ao PostgREST."""

from dataclasses import dataclass
from uuid import UUID

import httpx
from fastapi import HTTPException

from src.core.config import Settings


@dataclass(frozen=True)
class Identity:
    user_id: str
    owner_id: str
    email: str
    access_role: str


class SupabaseGateway:
    def __init__(self, settings: Settings, http: httpx.Client, token: str | None = None):
        self.settings, self.http, self.token = settings, http, token

    def request(self, method: str, path: str, *, params=None, json=None, prefer=None):
        headers = {"apikey": self.settings.publishable_key}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if prefer:
            headers["Prefer"] = prefer
        try:
            response = self.http.request(method, self.settings.supabase_url + path, headers=headers, params=params, json=json)
        except httpx.HTTPError as error:
            raise HTTPException(503, "Serviço de dados temporariamente indisponível.") from error
        if response.is_error:
            if response.status_code == 409:
                raise HTTPException(409, "Já existe um cliente com este CPF nesta conta.")
            if response.status_code == 429:
                raise HTTPException(429, "Muitas tentativas. Aguarde e tente novamente.")
            if response.status_code in (400, 401, 403) and path.startswith("/auth/"):
                raise HTTPException(401, "Credenciais inválidas ou sessão expirada.")
            if response.status_code in (401, 403):
                raise HTTPException(response.status_code, "Acesso não autorizado.")
            raise HTTPException(503, "Serviço de dados temporariamente indisponível.")
        return response.json() if response.content else None

    def identity(self) -> Identity:
        # Auth verifica assinatura e expiração; não decodificamos JWT sem validar.
        data = self.request("GET", "/auth/v1/user")
        metadata = data.get("app_metadata") or {}
        role = metadata.get("access_role", "operator")
        if data.get("is_anonymous") or role not in {"operator", "support"}:
            raise HTTPException(403, "Conta sem permissão para acessar os cadastros.")
        try:
            user_id = str(UUID(data["id"]))
            owner_id = str(UUID(metadata.get("data_owner_id") or user_id))
        except (ValueError, KeyError, TypeError) as error:
            raise HTTPException(403, "Configuração de acesso inválida.") from error
        return Identity(user_id, owner_id, data.get("email", ""), role)
