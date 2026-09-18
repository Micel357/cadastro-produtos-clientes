import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.servicos.armazenamento import JsonStore, storage


PAYLOAD = {"name": "Cliente Teste", "email": "teste@example.com", "phone": "85999990000", "city": "Fortaleza"}


@pytest.mark.parametrize("cpf", ["01234567890", "012.345.678-90"])
def test_cpf_is_normalized_and_persisted(cpf):
    with TestClient(app) as client:
        response = client.post("/api/clients", json={**PAYLOAD, "cpf": cpf})
        assert response.status_code == 201
        created = response.json()
        assert created["cpf"] == "01234567890"
        assert created in client.get("/api/clients").json()
        assert any(item.cpf == "01234567890" for item in JsonStore(storage.path).list_clients())


@pytest.mark.parametrize("cpf", [None, "", "123", "012345678901", "abc34567890", "012/345/678-90", "٠١٢٣٤٥٦٧٨٩٠", 12345678901])
def test_api_rejects_bad_cpf(cpf):
    with TestClient(app) as client:
        before = client.get("/api/clients").json()
        response = client.post("/api/clients", json={**PAYLOAD, "cpf": cpf})
        assert response.status_code == 422
        assert any(error["field"] == "body.cpf" for error in response.json()["errors"])
        assert client.get("/api/clients").json() == before


def test_cpf_required_for_new_clients_but_legacy_clients_still_load():
    with TestClient(app) as client:
        assert client.post("/api/clients", json=PAYLOAD).status_code == 422
        response = client.get("/api/clients")
        assert response.status_code == 200
        assert all(item["cpf"] == "" for item in response.json())
        assert client.get("/api/dashboard").status_code == 200
