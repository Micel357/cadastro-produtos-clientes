import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.clientes.schemas import Client, ClientCreate
from src.clientes.service import create_client, list_clients, remove_client
from src.core.config import settings
from src.core.logger import configure_logger
from src.produtos.schemas import Product, ProductCreate
from src.produtos.service import create_product, list_products, remove_product
from src.servicos.armazenamento import storage

configure_logger()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(_: FastAPI):
    storage.initialize()
    yield


app = FastAPI(title=settings.app_name, version="1.0.0", debug=False, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, error: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Dados inválidos.",
            "errors": [{"field": ".".join(map(str, issue["loc"])), "message": issue["msg"]} for issue in error.errors()],
        },
    )


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(_: Request, error: StarletteHTTPException) -> JSONResponse:
    if error.status_code == status.HTTP_404_NOT_FOUND:
        detail = "Recurso não encontrado."
    elif error.status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
        detail = "Erro interno do servidor."
    else:
        detail = str(error.detail)
    return JSONResponse(status_code=error.status_code, content={"detail": detail})


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, error: Exception) -> JSONResponse:
    logger.exception("Erro inesperado em %s", request.url.path, exc_info=error)
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": "Erro interno do servidor."})


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
