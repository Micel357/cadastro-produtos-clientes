import os
from pathlib import Path

import pytest

os.environ["DATA_FILE"] = str(Path(__file__).resolve().parents[2] / "data" / "test-cadastro.json")

from src.servicos.armazenamento import storage


@pytest.fixture(autouse=True)
def isolated_storage():
    storage.reset()
    storage.initialize()
    yield
    storage.reset()
