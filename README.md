# Vitrine & Clientes

Aplicação full stack para cadastro de produtos e clientes de uma pequena loja de papelaria. Os dados ficam somente em memória: ao reiniciar a API, a lista volta aos exemplos iniciais.

## Tecnologias escolhidas

- **Front-end:** React + TypeScript + Vite. React é mais simples de aprender e configurar do que Angular para este CRUD pequeno.
- **Back-end:** Python + FastAPI. A API fica curta, tipada e organizada em módulos por domínio.

## Estrutura

```text
cadastro-produtos-clientes/
├── assets/                 # Arquivos visuais reutilizáveis
├── backend/
│   ├── src/
│   │   ├── core/           # Configurações e logs
│   │   ├── clientes/       # Regras e esquemas de clientes
│   │   ├── produtos/       # Regras e esquemas de produtos
│   │   ├── servicos/       # Estado em memória e dados iniciais
│   │   └── main.py         # Entrada da API
│   ├── tests/              # Testes separados do código
│   └── requirements.txt
├── config/                 # Exemplos de configuração
├── data/                   # Dados locais opcionais (não usados como banco)
├── docs/                   # Documentação
├── deployment/nginx/        # Balanceador de carga Nginx
├── frontend/
│   └── src/
│       ├── components/     # Componentes de interface
│       ├── services/       # Comunicação com a API
│       ├── App.tsx
│       └── main.tsx
└── README.md
```

Essa organização segue o material: há uma pasta raiz, código em `src/`, módulos separados por responsabilidade, `tests/`, `docs/`, `assets/`, `config/`, `data/`, `.gitignore` e arquivos de dependências.

## Executar localmente

Em um terminal, inicie a API:

```bash
cd backend
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8000
```

Em outro terminal, inicie o front-end:

```bash
cd frontend
npm install
npm run dev
```

Abra `http://localhost:5173`. Para apontar para outra API, copie `config/.env.example` para `frontend/.env` e ajuste `VITE_API_URL`.

## Executar com alta disponibilidade

Com Docker instalado, esta configuração inicia duas APIs FastAPI, um Nginx que distribui as requisições entre elas e um volume com o arquivo JSON compartilhado:

```bash
docker compose up --build
```

Abra `http://localhost:8080`. Para executar o teste de disponibilidade, que para uma réplica e confirma que a outra continua respondendo, use:

```powershell
.\scripts\test-docker-availability.ps1
```

O projeto não utiliza banco de dados; usa `cadastro.json` no volume Docker compartilhado. Veja os limites dessa solução em `docs/arquitetura.md`.

## Rodar testes a partir da raiz

Depois de instalar as dependências Python em `backend/.venv`, execute na raiz do repositório:

```bash
backend\\.venv\\Scripts\\python -m pytest
```

O `pytest.ini` adiciona `backend` ao caminho de importação e procura os testes em `backend/tests`.

## Rotas da API

- `GET /health`
- `GET, POST, DELETE /api/products`
- `GET, POST, DELETE /api/clients`
- `GET /api/dashboard`
