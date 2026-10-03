"""AES-256-GCM com nonce aleatório e HMAC separado por conta e campo."""

import base64
import hashlib
import hmac
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class FieldCipher:
    def __init__(self, encryption_key: bytes, index_key: bytes):
        self.aes = AESGCM(encryption_key)
        self.index_key = index_key

    @staticmethod
    def context(owner: str, field: str) -> bytes:
        return f"v1:{owner}:{field}".encode()

    def encrypt(self, value: str, owner: str, field: str) -> str:
        nonce = os.urandom(12)
        encrypted = self.aes.encrypt(nonce, value.encode(), self.context(owner, field))
        return "v1:" + base64.b64encode(nonce + encrypted).decode()

    def decrypt(self, value: str, owner: str, field: str) -> str:
        if not value.startswith("v1:"):
            raise ValueError("Versão de criptografia desconhecida.")
        raw = base64.b64decode(value[3:], validate=True)
        return self.aes.decrypt(raw[:12], raw[12:], self.context(owner, field)).decode()

    def blind_index(self, value: str, owner: str, field: str) -> str:
        normalized = value.strip().casefold() if field == "email" else value.replace(".", "").replace("-", "")
        return hmac.new(self.index_key, self.context(owner, field) + b"\x00" + normalized.encode(), hashlib.sha256).hexdigest()


def mask(value: str, field: str) -> str:
    if field == "cpf":
        return f"{value[:3]}.***.***-{value[-2:]}" if value else ""
    if field == "email":
        return value[:1] + "***@***"
    return "***" + value[-4:]
