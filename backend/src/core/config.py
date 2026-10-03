"""Configuração validada no início da API; nenhum segredo tem valor padrão."""

import base64
import os
from dataclasses import dataclass, field
from urllib.parse import urlparse


def secret_key(name: str) -> bytes:
    try:
        key = base64.b64decode(os.environ[name], validate=True)
    except (KeyError, ValueError) as error:
        raise ValueError(f"Configure {name} em base64 (32 bytes).") from error
    if len(key) != 32:
        raise ValueError(f"{name} deve conter 32 bytes.")
    return key


@dataclass(frozen=True)
class Settings:
    supabase_url: str
    publishable_key: str = field(repr=False)
    encryption_key: bytes = field(repr=False)
    blind_index_key: bytes = field(repr=False)
    allowed_origins: tuple[str, ...] = ("http://localhost:5173", "http://localhost:8080")
    secure_cookies: bool = True
    app_name: str = "Vitrine & Clientes API"

    def __post_init__(self) -> None:
        url = urlparse(self.supabase_url)
        if url.scheme != "https" or not url.hostname or url.username or url.query or url.fragment or url.path not in ("", "/"):
            raise ValueError("SUPABASE_URL deve ser uma origem HTTPS.")
        if not self.publishable_key or self.publishable_key.startswith("sb_secret_"):
            raise ValueError("Use SUPABASE_PUBLISHABLE_KEY, nunca uma chave secret/service_role.")
        if self.publishable_key.count(".") == 2:
            import json
            try:
                part = self.publishable_key.split(".")[1]
                if json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4))).get("role") != "anon":
                    raise ValueError("A chave JWT legada precisa ser anon.")
            except (ValueError, KeyError) as error:
                raise ValueError("Chave pública inválida.") from error
        if len(self.encryption_key) != 32 or len(self.blind_index_key) != 32 or self.encryption_key == self.blind_index_key:
            raise ValueError("As chaves de criptografia e índice devem ter 32 bytes e ser diferentes.")
        if not self.allowed_origins or "*" in self.allowed_origins:
            raise ValueError("ALLOWED_ORIGINS deve listar origens explícitas.")
        if self.secure_cookies and any(not origin.startswith("https://") for origin in self.allowed_origins):
            raise ValueError("Use origens HTTPS ou COOKIE_SECURE=false apenas em desenvolvimento.")

    @classmethod
    def from_env(cls) -> "Settings":
        secure = os.getenv("COOKIE_SECURE", "true").lower()
        if secure not in {"true", "false"}:
            raise ValueError("COOKIE_SECURE deve ser true ou false.")
        return cls(
            supabase_url=os.getenv("SUPABASE_URL", "").rstrip("/"),
            publishable_key=os.getenv("SUPABASE_PUBLISHABLE_KEY", ""),
            encryption_key=secret_key("DATA_ENCRYPTION_KEY"),
            blind_index_key=secret_key("BLIND_INDEX_SECRET"),
            allowed_origins=tuple(x.strip().rstrip("/") for x in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:8080").split(",") if x.strip()),
            secure_cookies=secure == "true",
        )
