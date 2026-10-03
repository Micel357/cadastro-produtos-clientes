"""API autenticada, sem estado de cadastros ou sessões nas réplicas."""

import logging
import os
from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field, SecretStr
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.clientes.schemas import Client, ClientCreate
from src.core.config import Settings
from src.core.crypto import FieldCipher
from src.core.supabase import Identity, SupabaseGateway
from src.produtos.schemas import Product, ProductCreate
from src.servicos.database import Database

logger = logging.getLogger(__name__)
ACCESS_COOKIE = "cadastro_access"
REFRESH_COOKIE = "cadastro_refresh"


class Login(BaseModel):
    email: EmailStr
    password: SecretStr = Field(min_length=1, max_length=1024)


class ClientSearch(BaseModel):
    cpf: str

    def normalized(self) -> str:
        return ClientCreate.normalize_cpf(self.cpf)


def gateway(request: Request) -> SupabaseGateway:
    authorization = request.headers.get("Authorization", "")
    token = authorization[7:] if authorization.startswith("Bearer ") else request.cookies.get(ACCESS_COOKIE)
    if not token:
        raise HTTPException(401, "Entre na sua conta para continuar.")
    return SupabaseGateway(request.app.state.settings, request.app.state.http, token)


def current_identity(remote: SupabaseGateway = Depends(gateway)) -> Identity:
    return remote.identity()


def database(request: Request, identity: Identity = Depends(current_identity), remote: SupabaseGateway = Depends(gateway)) -> Database:
    return Database(remote, identity, request.app.state.cipher)


def writer(db: Database = Depends(database)) -> Database:
    if db.identity.access_role != "operator":
        raise HTTPException(403, "Seu perfil permite apenas consultar os cadastros.")
    return db


def require_origin(request: Request) -> None:
    # Clientes CLI podem usar Bearer; cookies do navegador exigem Origin explícita.
    if request.headers.get("Authorization", "").startswith("Bearer "):
        return
    if request.headers.get("Origin") not in request.app.state.settings.allowed_origins:
        raise HTTPException(403, "Origem da requisição não permitida.")


def clear_session(response: Response, secure: bool) -> None:
    response.delete_cookie(ACCESS_COOKIE, path="/api", secure=secure, httponly=True, samesite="lax")
    response.delete_cookie(REFRESH_COOKIE, path="/api/auth", secure=secure, httponly=True, samesite="lax")


def set_session(response: Response, session: dict, secure: bool) -> None:
    response.set_cookie(ACCESS_COOKIE, session["access_token"], max_age=int(session["expires_in"]), path="/api", secure=secure, httponly=True, samesite="lax")
    response.set_cookie(REFRESH_COOKIE, session["refresh_token"], max_age=7 * 86400, path="/api/auth", secure=secure, httponly=True, samesite="lax")


def create_app(config: Settings | None = None, transport: httpx.BaseTransport | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        settings = config or Settings.from_env()
        app.state.settings = settings
        app.state.cipher = FieldCipher(settings.encryption_key, settings.blind_index_key)
        with httpx.Client(timeout=10, limits=httpx.Limits(max_connections=30, max_keepalive_connections=10), transport=transport) as client:
            app.state.http = client
            yield

    app = FastAPI(title="Vitrine & Clientes API", version="2.0.0", debug=False, lifespan=lifespan)
    origins = config.allowed_origins if config else tuple(x.strip().rstrip("/") for x in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:8080").split(",") if x.strip())
    app.add_middleware(CORSMiddleware, allow_origins=list(origins), allow_credentials=True, allow_methods=["GET", "POST", "DELETE"], allow_headers=["Content-Type", "Authorization"])

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        settings = request.app.state.settings
        if settings.secure_cookies and request.url.path.startswith("/api") and request.url.scheme != "https":
            return JSONResponse(status_code=400, content={"detail": "Use HTTPS para acessar a API."}, headers={"Cache-Control": "no-store"})
        response = await call_next(request)
        if request.url.path.startswith("/api"):
            response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        if settings.secure_cookies and request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, error: RequestValidationError):
        return JSONResponse(status_code=422, content={"detail": "Dados inválidos.", "errors": [{"field": ".".join(map(str, issue["loc"])), "message": issue["msg"]} for issue in error.errors()]})

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, error: StarletteHTTPException):
        detail = "Recurso não encontrado." if error.status_code == 404 else str(error.detail)
        response = JSONResponse(status_code=error.status_code, content={"detail": detail})
        if error.status_code == 401 and request.url.path == "/api/auth/refresh":
            clear_session(response, request.app.state.settings.secure_cookies)
        return response

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, error: Exception):
        logger.error("Falha %s em %s", type(error).__name__, request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Erro interno do servidor."})

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/api/auth/login", dependencies=[Depends(require_origin)])
    def login(payload: Login, request: Request, response: Response):
        remote = SupabaseGateway(request.app.state.settings, request.app.state.http)
        session = remote.request("POST", "/auth/v1/token", params={"grant_type": "password"}, json={"email": str(payload.email), "password": payload.password.get_secret_value()})
        remote.token = session["access_token"]
        user = remote.identity()
        set_session(response, session, request.app.state.settings.secure_cookies)
        return {"email": user.email, "access_role": user.access_role}

    @app.post("/api/auth/refresh", dependencies=[Depends(require_origin)])
    def refresh(request: Request, response: Response):
        refresh_token = request.cookies.get(REFRESH_COOKIE)
        if not refresh_token:
            raise HTTPException(401, "Sessão expirada. Entre novamente.")
        remote = SupabaseGateway(request.app.state.settings, request.app.state.http)
        session = remote.request("POST", "/auth/v1/token", params={"grant_type": "refresh_token"}, json={"refresh_token": refresh_token})
        set_session(response, session, request.app.state.settings.secure_cookies)
        return {"status": "ok"}

    @app.post("/api/auth/logout", dependencies=[Depends(require_origin)])
    def logout(request: Request):
        response = Response(status_code=204)
        authorization = request.headers.get("Authorization", "")
        token = authorization[7:] if authorization.startswith("Bearer ") else request.cookies.get(ACCESS_COOKIE)
        if token:
            try:
                SupabaseGateway(request.app.state.settings, request.app.state.http, token).request("POST", "/auth/v1/logout", params={"scope": "local"})
            except HTTPException as error:
                if error.status_code != 401:
                    logger.warning("Sessão local encerrada; revogação remota indisponível (%s).", error.status_code)
        clear_session(response, request.app.state.settings.secure_cookies)
        return response

    @app.get("/api/auth/session")
    def session(identity: Identity = Depends(current_identity)):
        return {"email": identity.email, "access_role": identity.access_role}

    @app.get("/api/dashboard")
    def dashboard(db: Database = Depends(database)):
        return db.dashboard()

    @app.get("/api/products", response_model=list[Product])
    def products(db: Database = Depends(database)):
        return db.list_products()

    @app.post("/api/products", response_model=Product, status_code=201, dependencies=[Depends(require_origin)])
    def add_product(payload: ProductCreate, db: Database = Depends(writer)):
        return db.create_product(payload)

    @app.delete("/api/products/{row_id}", status_code=204, dependencies=[Depends(require_origin)])
    def remove_product(row_id: int, db: Database = Depends(writer)):
        if not db.remove("products", row_id):
            raise HTTPException(404)

    @app.get("/api/clients", response_model=list[Client])
    def clients(db: Database = Depends(database)):
        return db.list_clients()

    @app.post("/api/clients", response_model=Client, status_code=201, dependencies=[Depends(require_origin)])
    def add_client(payload: ClientCreate, db: Database = Depends(writer)):
        return db.create_client(payload)

    @app.post("/api/clients/search", response_model=list[Client], dependencies=[Depends(require_origin)])
    def find_client(payload: ClientSearch, db: Database = Depends(writer)):
        try:
            cpf = payload.normalized()
        except ValueError as error:
            raise HTTPException(422, "Informe um CPF com 11 dígitos.") from error
        index = db.cipher.blind_index(cpf, db.identity.owner_id, "cpf")
        return db.list_clients({"cpf_bindex": f"eq.{index}"})

    @app.delete("/api/clients/{row_id}", status_code=204, dependencies=[Depends(require_origin)])
    def remove_client(row_id: int, db: Database = Depends(writer)):
        if not db.remove("clients", row_id):
            raise HTTPException(404)

    return app


app = create_app()
