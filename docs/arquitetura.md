# Arquitetura

O projeto usa duas aplicações independentes.

```text
Interface React -> HTTP/JSON -> API FastAPI -> lista em memória
```

As listas em memória substituem temporariamente um banco de dados. A troca futura por PostgreSQL, SQLite ou outra fonte deve acontecer apenas no módulo `backend/src/servicos/memoria.py`, preservando as rotas, os esquemas e a interface.

## Responsabilidades

- `core/`: configurações e registros de execução.
- `produtos/` e `clientes/`: validação e regras de cada domínio.
- `servicos/`: dados iniciais e armazenamento em memória.
- `components/`: formulários, indicadores e listas reutilizáveis.
- `services/`: uma única camada para chamadas HTTP do front-end.
