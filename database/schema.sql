-- Instalação inicial em um projeto Supabase vazio (PostgreSQL 15+).
-- Aplicar como postgres; não executar com JWT de usuário ou na inicialização da API.
begin;

create schema if not exists extensions;
create extension if not exists pgcrypto with schema extensions;
create schema cadastro_private;
revoke all on schema cadastro_private from public, anon, authenticated;

-- Somente app_metadata, alterável por administradores, define escopo e perfil.
create function cadastro_private.owner_id() returns uuid
language sql stable security invoker set search_path = '' as $$
  select coalesce(nullif(auth.jwt()->'app_metadata'->>'data_owner_id', '')::uuid, auth.uid());
$$;
create function cadastro_private.access_role() returns text
language sql stable security invoker set search_path = '' as $$
  select case when coalesce((auth.jwt()->>'is_anonymous')::boolean, false)
    then 'denied' else coalesce(auth.jwt()->'app_metadata'->>'access_role', 'operator') end;
$$;
revoke all on function cadastro_private.owner_id(), cadastro_private.access_role() from public;
grant usage on schema cadastro_private to authenticated;
grant execute on function cadastro_private.owner_id(), cadastro_private.access_role() to authenticated;

create table public.products (
  id bigint generated always as identity primary key,
  owner_id uuid not null references auth.users(id),
  name varchar(80) not null check (length(btrim(name)) >= 2),
  category varchar(50) not null check (length(btrim(category)) >= 2),
  price numeric(12,2) not null check (price > 0 and price != 'NaN'::numeric),
  stock integer not null check (stock >= 0),
  description varchar(180) not null default '',
  created_at timestamptz not null default now()
);
create index products_owner_id_id on public.products(owner_id, id);

create table public.clients (
  id bigint generated always as identity primary key,
  owner_id uuid not null references auth.users(id),
  name varchar(80) not null check (length(btrim(name)) >= 2),
  city varchar(60) not null check (length(btrim(city)) >= 2),
  cpf_encrypted text check (cpf_encrypted like 'v1:%'),
  cpf_bindex varchar(64) check (cpf_bindex ~ '^[0-9a-f]{64}$'),
  cpf_masked varchar(20) not null default '',
  email_encrypted text not null check (email_encrypted like 'v1:%'),
  email_bindex varchar(64) not null check (email_bindex ~ '^[0-9a-f]{64}$'),
  email_masked varchar(254) not null,
  phone_encrypted text not null check (phone_encrypted like 'v1:%'),
  phone_masked varchar(20) not null,
  created_at timestamptz not null default now(),
  constraint clients_cpf_pair check ((cpf_encrypted is null) = (cpf_bindex is null)),
  constraint clients_owner_cpf_unique unique (owner_id, cpf_bindex)
);
-- UNIQUE já fornece o índice de CPF: não cria um B-Tree duplicado como no PDF.
create index clients_owner_id_id on public.clients(owner_id, id);
create index clients_owner_email on public.clients(owner_id, email_bindex);

alter table public.clients enable row level security;
alter table public.clients force row level security;
alter table public.products enable row level security;
alter table public.products force row level security;
revoke all on public.clients, public.products from public, anon, authenticated;
grant select, insert, delete on public.clients, public.products to authenticated;
grant usage on sequence public.clients_id_seq, public.products_id_seq to authenticated;

create policy clients_read on public.clients for select to authenticated
using (owner_id = (select cadastro_private.owner_id()) and (select cadastro_private.access_role()) in ('operator', 'support'));
create policy clients_insert on public.clients for insert to authenticated
with check (owner_id = (select cadastro_private.owner_id()) and (select cadastro_private.access_role()) = 'operator');
create policy clients_delete on public.clients for delete to authenticated
using (owner_id = (select cadastro_private.owner_id()) and (select cadastro_private.access_role()) = 'operator');
create policy products_read on public.products for select to authenticated
using (owner_id = (select cadastro_private.owner_id()) and (select cadastro_private.access_role()) in ('operator', 'support'));
create policy products_insert on public.products for insert to authenticated
with check (owner_id = (select cadastro_private.owner_id()) and (select cadastro_private.access_role()) = 'operator');
create policy products_delete on public.products for delete to authenticated
using (owner_id = (select cadastro_private.owner_id()) and (select cadastro_private.access_role()) = 'operator');

-- Invoker mantém as mesmas políticas RLS da tabela; nenhuma chave no banco.
create view public.clients_support with (security_invoker = true) as
select id, owner_id, name, city, cpf_masked as cpf, email_masked as email, phone_masked as phone
from public.clients;
revoke all on public.clients_support from public, anon;
grant select on public.clients_support to authenticated;

create function public.dashboard_totals(p_owner uuid) returns jsonb
language sql stable security invoker set search_path = '' as $$
  select jsonb_build_object(
    'products', count(*),
    'clients', (select count(*) from public.clients where owner_id = p_owner),
    'stock', coalesce(sum(stock), 0),
    'inventory_value', coalesce(sum(price * stock), 0)
  ) from public.products where owner_id = p_owner;
$$;
revoke all on function public.dashboard_totals(uuid) from public, anon;
grant execute on function public.dashboard_totals(uuid) to authenticated;

create table cadastro_private.audit_ledger (
  id bigserial primary key,
  occurred_at timestamptz not null,
  actor uuid not null,
  action text not null,
  details jsonb not null,
  previous_hash varchar(64) not null,
  current_hash varchar(64) not null
);
create table cadastro_private.audit_head (
  singleton boolean primary key default true check (singleton),
  last_id bigint not null default 0,
  event_count bigint not null default 0,
  last_hash varchar(64) not null default repeat('0', 64)
);
insert into cadastro_private.audit_head(singleton) values (true);
alter table cadastro_private.audit_ledger enable row level security;
alter table cadastro_private.audit_head enable row level security;
revoke all on cadastro_private.audit_ledger, cadastro_private.audit_head from public, anon, authenticated;

-- Uma só representação canônica é utilizada pelo trigger e pelo verificador.
create function cadastro_private.audit_payload(
  event_id bigint, event_time timestamptz, event_actor uuid, event_action text,
  event_details jsonb, prior_hash text
) returns text language sql immutable security invoker set search_path = '' as $$
  select jsonb_build_array(event_id,
    to_char(event_time at time zone 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"'),
    event_actor, event_action, event_details, prior_hash)::text;
$$;

-- Definer necessário somente para escrever a auditoria privada no mesmo commit.
-- Sem acesso público/RPC, search_path fixo, ator e escopo verificados novamente.
create function cadastro_private.record_change() returns trigger
language plpgsql security definer set search_path = '' as $$
declare
  event_row jsonb;
  prior_hash text;
  event_id bigint;
  event_time timestamptz;
  event_actor uuid := auth.uid();
  event_action text;
  event_details jsonb;
  event_hash text;
begin
  if event_actor is null or tg_table_schema != 'public' or tg_table_name not in ('clients', 'products') then
    raise exception 'Unauthorized audit operation' using errcode = '42501';
  end if;
  event_row := case when tg_op = 'DELETE' then to_jsonb(old) else to_jsonb(new) end;
  if (event_row->>'owner_id')::uuid != cadastro_private.owner_id()
     or cadastro_private.access_role() != 'operator' then
    raise exception 'Unauthorized owner' using errcode = '42501';
  end if;
  -- A linha única serializa escritores de todas as réplicas até o commit/rollback.
  select last_hash into prior_hash from cadastro_private.audit_head where singleton for update;
  event_id := nextval('cadastro_private.audit_ledger_id_seq');
  event_time := clock_timestamp();
  event_action := tg_table_name || '.' || lower(tg_op);
  -- Nunca copia CPF, e-mail, telefone, ciphertext ou dados de formulário para logs.
  event_details := jsonb_build_object('row_id', event_row->'id', 'owner_id', event_row->'owner_id',
    'row_hash', encode(extensions.digest(convert_to(event_row::text, 'UTF8'), 'sha256'), 'hex'));
  event_hash := encode(extensions.digest(convert_to(cadastro_private.audit_payload(
    event_id, event_time, event_actor, event_action, event_details, prior_hash), 'UTF8'), 'sha256'), 'hex');
  insert into cadastro_private.audit_ledger values
    (event_id, event_time, event_actor, event_action, event_details, prior_hash, event_hash);
  update cadastro_private.audit_head set last_id = event_id, last_hash = event_hash,
    event_count = event_count + 1 where singleton;
  return null;
end;
$$;

create function cadastro_private.reject_audit_change() returns trigger
language plpgsql security invoker set search_path = '' as $$
begin
  raise exception 'Audit ledger is append-only' using errcode = '42501';
end;
$$;
create trigger audit_no_mutation before update or delete on cadastro_private.audit_ledger
for each row execute function cadastro_private.reject_audit_change();
create trigger audit_no_truncate before truncate on cadastro_private.audit_ledger
for each statement execute function cadastro_private.reject_audit_change();
create trigger clients_audit after insert or update or delete on public.clients
for each row execute function cadastro_private.record_change();
create trigger products_audit after insert or update or delete on public.products
for each row execute function cadastro_private.record_change();
revoke all on function cadastro_private.record_change(), cadastro_private.reject_audit_change() from public, anon, authenticated;
revoke all on function cadastro_private.audit_payload(bigint, timestamptz, uuid, text, jsonb, text) from public, anon, authenticated;
revoke all on sequence cadastro_private.audit_ledger_id_seq from public, anon, authenticated;

commit;
