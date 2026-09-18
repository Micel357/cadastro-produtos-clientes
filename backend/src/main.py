import logging

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from src.clientes.schemas import Client, ClientCreate
from src.clientes.service import create_client, list_clients, remove_client
from src.core.config import settings
from src.core.logger import configure_logger
from src.produtos.schemas import Product, ProductCreate
from src.produtos.service import create_product, list_products, remove_product

configure_logger()
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name, version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/dashboard")
def dashboard() -> dict[str, int | float]:
    products = list_products()
    return {
        "products": len(products),
        "clients": len(list_clients()),
        "stock": sum(product.stock for product in products),
        "inventory_value": round(sum(product.price * product.stock for product in products), 2),
    }


@app.get("/api/products", response_model=list[Product])
def get_products() -> list[Product]:
    return list_products()


@app.post("/api/products", response_model=Product, status_code=status.HTTP_201_CREATED)
def post_product(payload: ProductCreate) -> Product:
    product = create_product(payload)
    logger.info("Produto cadastrado: %s", product.id)
    return product


@app.delete("/api/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int) -> None:
    if not remove_product(product_id):
        raise HTTPException(status_code=404, detail="Produto não encontrado.")


@app.get("/api/clients", response_model=list[Client])
def get_clients() -> list[Client]:
    return list_clients()


@app.post("/api/clients", response_model=Client, status_code=status.HTTP_201_CREATED)
def post_client(payload: ClientCreate) -> Client:
    client = create_client(payload)
    logger.info("Cliente cadastrado: %s", client.id)
    return client


@app.delete("/api/clients/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(client_id: int) -> None:
    if not remove_client(client_id):
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")
