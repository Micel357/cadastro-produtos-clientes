from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    app_name: str = "Vitrine & Clientes API"
    allowed_origins: tuple[str, ...] = tuple(
        origin.strip()
        for origin in os.getenv(
            "ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",")
        if origin.strip()
    )
    data_file: str = os.getenv("DATA_FILE", "data/cadastro.json")


settings = Settings()
