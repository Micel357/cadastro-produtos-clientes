# Vitrine & Clientes

Cadastro de clientes e produtos com React + TypeScript + Vite e FastAPI. Os dados
persistem no PostgreSQL do Supabase, compartilhado pelas réplicas da API.
O acesso exige uma conta no Supabase Auth.

## Preparar o Supabase

1. Crie um projeto PostgreSQL 15+ e aplique `database/schema.sql` uma vez, pelo
   SQL Editor ou como migração. O script é transacional e falha se a estrutura já
   existir, evitando substituir dados.
2. Crie o primeiro usuário no painel **Authentication → Users**. Desative inscrições
   públicas se somente funcionários puderem acessar. Use expiração curta dos tokens
   (por exemplo, 15 minutos), proteção contra senhas vazadas quando disponível e os
   limites de tentativas do Auth.
3. Copie a URL HTTPS e a **publishable key** para `.env`. A aplicação não usa
   `service_role` nem senha administrativa do PostgreSQL.
4. Cada usuário vê seus próprios cadastros por padrão. Para compartilhar os dados da
   loja ou atribuir suporte, configure **app_metadata** administrativamente conforme
   [arquitetura e segurança](docs/arquitetura.md). `user_metadata` não concede acesso.

## Configurar e executar

Na raiz:

```bash
cp config/.env.example .env
python scripts/generate_keys.py
```

Preencha `SUPABASE_URL` e `SUPABASE_PUBLISHABLE_KEY` em `.env`. O gerador grava duas
chaves independentes de 32 bytes e preserva as existentes. Guarde backup seguro:
perder a chave de criptografia impede recuperar os campos protegidos.

API (Python 3.12):

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.main:app --reload --env-file ../.env --port 8000
```

No Windows, ative com `.venv\\Scripts\\Activate.ps1`.

Interface (Node.js 22):

```bash
cd frontend
corepack enable
pnpm install --frozen-lockfile
pnpm dev
```

Abra http://localhost:5173. O Vite encaminha `/api` para a API local, mantendo cookies
na mesma origem. `VITE_API_URL` normalmente fica vazio; nunca acrescente `/api` ao
seu valor, pois as rotas já contêm esse prefixo.

Para duas réplicas e Nginx:

```bash
docker compose up --build
```

Abra http://localhost:8080. As duas APIs utilizam o mesmo Supabase e as mesmas chaves,
sem arquivos JSON compartilhados ou sessões locais. O gateway fica ligado ao loopback
no exemplo local. O teste de disponibilidade é `scripts/test-docker-availability.ps1`;
ele verifica a continuidade do gateway, não a disponibilidade do Supabase.

## Produção

- Publique interface e `/api` na mesma origem HTTPS, atrás de um proxy TLS confiável.
  O Compose é um exemplo local, não um terminador TLS de produção.
- Configure `COOKIE_SECURE=true` e `ALLOWED_ORIGINS=https://seu-dominio`.
  Cookies são HttpOnly, SameSite=Lax e não ficam em localStorage.
  A API recusa HTTP nesse modo. Configure `FORWARDED_ALLOW_IPS` no Uvicorn com os
  proxies confiáveis do seu provedor para reconhecer a terminação TLS corretamente.
- Armazene segredos no provedor de hospedagem. `render.yaml` lista as variáveis
  necessárias; aplicar o banco não configura automaticamente um serviço Render existente.
- O tráfego API → Supabase exige HTTPS com validação de certificado.
- Configure backups do banco, retenção e verificação periódica da auditoria.
  Não há promessa de alta disponibilidade do banco em um plano gratuito.

## Dados da versão anterior

A aplicação não volta ao JSON se o banco ficar indisponível e não insere exemplos
automaticamente. Nenhum arquivo `cadastro.json` real acompanha o repositório.
Preserve o volume/arquivo antigo até concluir a transferência dos seus cadastros.
Clientes antigos sem CPF precisam desse campo preenchido antes de serem cadastrados
na nova API. Não invente CPFs nem transfira os exemplos como clientes reais.
Não execute `docker compose down -v` no ambiente antigo antes de fazer backup.
A API continua usando IDs numéricos; os IDs são gerados pelo PostgreSQL.

## Verificação

```bash
pip install -r backend/requirements-dev.txt
python -m pytest -q
```

Sem `TEST_DATABASE_URL`, os testes HTTP e de criptografia rodam, e os testes de
PostgreSQL são explicitamente pulados. Para verificar RLS, concorrência e auditoria,
use um banco **descartável**, cujo nome termine em `_test`:

```bash
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/cadastro_test python -m pytest -q
```

Esses testes recriam os schemas do banco de testes. Nunca aponte essa variável para
o projeto Supabase real. O workflow `.github/workflows/ci.yml` cria PostgreSQL 17
descartável, executa toda a suíte e compila a interface.

Verificação operacional do ledger:

```bash
# AUDIT_DATABASE_URL e PGSSLROOTCERT devem vir do gerenciador de segredos.
python scripts/verify_audit.py
python scripts/verify_audit.py --checkpoint /caminho/seguro/checkpoint-anterior.json
```

A saída JSON contém somente o cabeçalho da auditoria. Guarde-a em armazenamento
externo protegido para detectar reescrita completa do histórico.

## Rotas

- `GET /health`: processo vivo, sem revelar dados.
- `POST /api/auth/login`, `POST /api/auth/refresh`, `POST /api/auth/logout`.
- `GET /api/auth/session`.
- `GET, POST /api/products`; `DELETE /api/products/{id}`.
- `GET, POST /api/clients`; `DELETE /api/clients/{id}`.
- `POST /api/clients/search`: busca por CPF normalizado sem colocá-lo na URL.
- `GET /api/dashboard`: totais calculados no banco sob RLS.

Rotas de dados exigem sessão ou `Authorization: Bearer <JWT do usuário>`.
Requisições que alteram dados por cookies exigem `Origin` autorizado.
O perfil `support` consulta dados mascarados e não pode gravar ou pesquisar CPF.
