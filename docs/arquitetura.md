# Arquitetura

O projeto usa duas aplicações independentes.

```text
Interface React -> HTTP/JSON -> API FastAPI -> lista em memória
```

## Disponibilidade e dados compartilhados

O arquivo `docker-compose.yml` executa duas instâncias (`api-1` e `api-2`) e o Nginx, no serviço `gateway`, distribui as requisições com `least_conn`. Quando uma instância falha, o Nginx marca falhas temporárias e tenta a outra instância em erros de conexão, timeout, 502, 503 e 504.

```text
Navegador -> gateway Nginx -> api-1 FastAPI --┐
                                               ├-> cadastro.json (volume Docker compartilhado)
                           -> api-2 FastAPI --┘
```

Execute com `docker compose up --build` e abra `http://localhost:8080`.

O arquivo JSON compartilhado mantém os cadastros iguais entre as duas réplicas sem usar banco de dados. As gravações têm bloqueio exclusivo e substituição atômica do arquivo. Essa solução é suficiente para o projeto acadêmico, mas não substitui um banco em produção.

## Segurança e integridade

- Erros de validação, 404 e falhas inesperadas recebem respostas padronizadas. A exceção completa fica somente no log do servidor; a resposta ao cliente não expõe segredos ou detalhes internos.
- O valor total do estoque é calculado na API a partir dos produtos guardados no arquivo compartilhado. O front-end não envia esse total.

As listas em memória substituem temporariamente um banco de dados. A troca futura por PostgreSQL, SQLite ou outra fonte deve acontecer apenas no módulo `backend/src/servicos/memoria.py`, preservando as rotas, os esquemas e a interface.

## Responsabilidades

- `core/`: configurações e registros de execução.
- `produtos/` e `clientes/`: validação e regras de cada domínio.
- `servicos/`: dados iniciais e armazenamento em memória.
- `components/`: formulários, indicadores e listas reutilizáveis.
- `services/`: uma única camada para chamadas HTTP do front-end.
