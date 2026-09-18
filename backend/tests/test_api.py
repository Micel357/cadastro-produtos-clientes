from fastapi.testclient import TestClient

import src.main as main


def test_health_and_dashboard_are_served() -> None:
    with TestClient(main.app) as client:
        assert client.get("/health").json() == {"status": "ok"}
        dashboard = client.get("/api/dashboard").json()

    assert dashboard == {"products": 2, "clients": 2, "stock": 60, "inventory_value": 853.2}


def test_api_rejects_invalid_product_with_standard_error() -> None:
    with TestClient(main.app) as client:
        response = client.post("/api/products", json={"name": "A", "category": "", "price": 0, "stock": -1})

    assert response.status_code == 422
    assert response.json()["detail"] == "Dados inválidos."
    assert response.json()["errors"]


def test_api_creates_product_and_calculates_inventory_on_server() -> None:
    payload = {"name": "Estojo", "category": "Organização", "price": 20, "stock": 3, "description": "Azul"}
    with TestClient(main.app) as client:
        created = client.post("/api/products", json=payload)
        dashboard = client.get("/api/dashboard").json()

    assert created.status_code == 201
    assert dashboard["products"] == 3
    assert dashboard["inventory_value"] == 913.2


def test_api_returns_safe_errors_without_exception_details(monkeypatch) -> None:
    def fail() -> list[object]:
        raise RuntimeError("API_SECRET_SHOULD_NOT_LEAK")

    monkeypatch.setattr(main, "list_products", fail)
    with TestClient(main.app, raise_server_exceptions=False) as client:
        response = client.get("/api/dashboard")

    assert response.status_code == 500
    assert response.json() == {"detail": "Erro interno do servidor."}
    assert "API_SECRET_SHOULD_NOT_LEAK" not in response.text


def test_api_handles_not_found_and_cors() -> None:
    with TestClient(main.app) as client:
        missing = client.delete("/api/products/999")
        cors = client.options("/api/products", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"})

    assert missing.status_code == 404
    assert missing.json() == {"detail": "Recurso não encontrado."}
    assert cors.status_code == 200
    assert cors.headers["access-control-allow-origin"] == "http://localhost:5173"
