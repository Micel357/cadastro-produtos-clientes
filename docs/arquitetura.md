# Arquitetura e segurança

```text
Navegador → HTTPS / proxy → FastAPI (réplicas sem estado)
                              ├→ Supabase Auth
                              └→ PostgREST HTTPS + JWT do usuário
                                  → PostgreSQL + RLS + auditoria
```

## Responsabilidades

- `core/config.py`: valida URLs, origens e chaves; falha ao iniciar se faltar configuração.
- `core/supabase.py`: valida sessão no Auth e repassa o JWT ao PostgREST. Nunca usa
  service_role, que ignoraria as políticas RLS.
- `core/crypto.py`: AES-256-GCM e HMAC-SHA256.
- `servicos/database.py`: única implementação da persistência.
- `clientes/` e `produtos/`: contratos e validação de entrada.
- `database/schema.sql`: tabelas, constraints, políticas, view, funções e triggers.
- `scripts/verify_audit.py`: verificação independente de SHA-256 sobre representação
  canônica gerada pelo mesmo contrato SQL.
- Frontend: login, sessão e cadastros. Não recebe as chaves de criptografia.

Foram removidos JsonStore e os serviços que somente encaminhavam chamadas.
Os testes do JSON foram substituídos por testes de criptografia, sessão, PostgREST
e PostgreSQL real. O README não descreve mais memória, JSON ou `memoria.py` como banco.

## Autenticação e escopos

O Supabase Auth administra senhas (bcrypt e salt), assinatura, expiração e renovação
dos tokens. A FastAPI consulta `/auth/v1/user`; não confia em JWT decodificado sem
validação. Cookies HttpOnly ficam limitados a `/api` e `/api/auth`, com Secure em
produção e SameSite=Lax. Operações com cookies verificam a origem contra uma lista
explícita; o frontend não guarda tokens em localStorage.
No modo de produção, chamadas HTTP à API são recusadas. O proxy deve terminar TLS
e ser explicitamente confiável pelo Uvicorn. Logout sempre apaga os cookies locais;
se a revogação remota falhar, registra a falha sem revelar tokens.

Todo usuário possui um escopo de dados por padrão: seu próprio UUID. Um administrador
pode configurar `app_metadata`:

```json
{
  "access_role": "support",
  "data_owner_id": "UUID-DO-RESPONSAVEL-PELA-LOJA"
}
```

`operator` permite consultar, cadastrar e excluir nesse escopo; `support` permite
somente consultar. O padrão é operator com escopo próprio. Atribua o mesmo
`data_owner_id` aos funcionários da mesma loja. Não armazene permissões em
`user_metadata`, que o usuário pode editar. Desabilite cadastro público se o sistema
for exclusivo para funcionários.

RLS compara `owner_id` com o escopo derivado do JWT validado pelo PostgREST.
As tabelas não concedem acesso ao papel anon. Não há UPDATE enquanto a aplicação
não oferecer edição. As consultas da API também filtram o escopo atual.
Alterações de app_metadata e logout não tornam instantaneamente inválida toda cópia
de um access token já emitido: use expiração curta e revogue sessões na administração.
A API consulta metadados atuais; políticas no banco veem os claims do token até renovar.

## Criptografia e busca

CPF, e-mail e telefone são criptografados antes de sair da API. Cada gravação usa
um nonce aleatório de 96 bits e AES-256-GCM. O contexto autenticado vincula o campo
à conta, impedindo mover ciphertext entre contas ou entre campos sem detecção.
Nome e cidade continuam consultáveis em texto; o projeto não afirma criptografar
todas as informações pessoais.

A chave DATA_ENCRYPTION_KEY é independente de BLIND_INDEX_SECRET. Nenhuma tem valor
padrão ou fica no Git/banco. CPF normalizado e e-mail em casefold recebem índices
HMAC-SHA256 com separação por campo e conta. O CPF é único por conta; o UNIQUE já
cria o índice B-Tree, eliminando o índice redundante do exemplo do PDF. E-mails
têm índice de busca, mas podem ser compartilhados por clientes.

Valores monetários são Decimal na validação e numeric(12,2) no banco. Valores
negativos, NaN, infinito e mais de duas casas decimais são rejeitados.
As consultas PostgREST passam parâmetros estruturados, sem concatenar SQL de usuários.

A view clients_support usa security_invoker e obedece RLS. Ela retorna apenas
máscaras persistidas e dados não criptografados. Usuários autenticados podem alcançar
seus próprios ciphertexts pelo Data API, mas a chave de decriptação existe somente
na API; suporte não possui rota de decriptação. Máscaras revelam deliberadamente
partes limitadas de dados para atendimento.

## Auditoria

Triggers registram mudanças de clientes/produtos na mesma transação. O schema
cadastro_private não é exposto pelo Data API. Usuários da aplicação não podem
inserir, editar, excluir ou truncar o ledger. A função SECURITY DEFINER se limita
ao trigger interno, verifica o ator e o escopo, fixa search_path e tem EXECUTE
revogado de PUBLIC/anon/authenticated.

O trigger bloqueia a linha audit_head com FOR UPDATE antes de gerar o evento e
seu hash. Assim, escritores concorrentes não reutilizam o mesmo predecessor.
Rollback desfaz cadastro, evento e cabeçalho juntos; lacunas na sequência são normais.

O payload canônico inclui ID, timestamp UTC de precisão fixa, ator, ação, metadados
mínimos e hash anterior. Não contém dados de formulário nem ciphertext.
O verificador recalcula SHA-256 do mesmo texto UTF-8, evitando a divergência do PDF
entre jsonb::text no PostgreSQL e dict/timestamp convertidos em Python.

O cabeçalho guarda ID, contagem e hash finais. A verificação usa uma transação
REPEATABLE READ e também detecta remoção da cauda que uma comparação simples de
hashes anteriores não detectaria. Uma âncora externa permite comparar um histórico
anteriormente observado.

Este mecanismo oferece restrição de escrita e evidência de adulteração. Um
superusuário capaz de desativar triggers e reescrever ledger, funções e cabeçalho
pode forjar uma cadeia inteira. Para esse cenário é necessária âncora externa
protegida, além de separação de privilégios e monitoramento. Hash chaining sozinho
não fornece não-repúdio ou imutabilidade absoluta contra o DBA.

## Operação

Faça backup de banco e chaves em locais separados. A troca das chaves exige
recriptografar dados/recalcular índices, não apenas editar .env. Execute auditorias
agendadas por uma identidade administrativa separada da aplicação, usando TLS com
validação de hostname e CA. Não dê acesso ao ledger aos usuários do navegador.

A API usa pool HTTP limitado e timeouts. Auth aplica seus limites de tentativas;
configure limites adicionais e TLS no gateway de produção. Duas réplicas melhoram
a disponibilidade da aplicação, mas não substituem backups nem um plano adequado
de disponibilidade do banco. /health é liveness do processo.
