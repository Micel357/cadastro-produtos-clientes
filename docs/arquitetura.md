# Arquitetura

O projeto usa duas aplicações independentes.

```text
Interface React -> HTTP/JSON -> API FastAPI -> lista em memória
```

## Disponibilidade

O arquivo `docker-compose.yml` executa duas instâncias (`api-1` e `api-2`) e o Nginx, no serviço `gateway`, distribui as requisições com `least_conn`. Quando uma instância falha, o Nginx marca falhas temporárias e tenta a outra instância em erros de conexão, timeout, 502, 503 e 504.

```text
Navegador -> gateway Nginx -> api-1 FastAPI
                           -> api-2 FastAPI
```

Execute com `docker compose up --build` e abra `http://localhost:8080`.

> Limitação consciente desta versão: os dados ficam na memória de cada API. O balanceamento mantém a aplicação respondendo se uma instância cair, mas cadastros não são compartilhados entre réplicas. Para disponibilidade completa de operações de escrita, a próxima evolução deve usar uma fonte compartilhada, como PostgreSQL ou Redis.

As listas em memória substituem temporariamente um banco de dados. A troca futura por PostgreSQL, SQLite ou outra fonte deve acontecer apenas no módulo `backend/src/servicos/memoria.py`, preservando as rotas, os esquemas e a interface.

## Responsabilidades

- `core/`: configurações e registros de execução.
- `produtos/` e `clientes/`: validação e regras de cada domínio.
- `servicos/`: dados iniciais e armazenamento em memória.
- `components/`: formulários, indicadores e listas reutilizáveis.
- `services/`: uma única camada para chamadas HTTP do front-end.
