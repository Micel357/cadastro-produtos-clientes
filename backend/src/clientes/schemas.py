import re

from pydantic import BaseModel, EmailStr, Field, field_validator


class ClientCreate(BaseModel):
    cpf: str
    name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    phone: str = Field(min_length=8, max_length=20)
    city: str = Field(min_length=2, max_length=60)

    @field_validator("cpf")
    @classmethod
    def normalize_cpf(cls, value: str) -> str:
        if not re.fullmatch(r"(?:[0-9]{11}|[0-9]{3}\.[0-9]{3}\.[0-9]{3}-[0-9]{2})", value):
            raise ValueError("Informe o CPF com 11 números ou no formato 000.000.000-00.")
        return value.replace(".", "").replace("-", "")


class Client(ClientCreate):
    id: int
    # Cadastros anteriores à inclusão do CPF continuam disponíveis para leitura.
    cpf: str = ""
