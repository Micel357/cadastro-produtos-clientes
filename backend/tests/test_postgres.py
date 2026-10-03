"""Testes reais de PostgreSQL; somente um banco descartável com nome *_test."""

import json
import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from verify_audit import verify_ledger

ROOT = Path(__file__).resolve().parents[2]
OWNER = "11111111-1111-4111-8111-111111111111"
OTHER = "22222222-2222-4222-8222-222222222222"


@unittest.skipUnless(os.getenv("TEST_DATABASE_URL"), "Defina TEST_DATABASE_URL para PostgreSQL descartável.")
class PostgresSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import psycopg
        cls.psycopg = psycopg
        cls.url = os.environ["TEST_DATABASE_URL"]
        with psycopg.connect(cls.url) as connection:
            if not connection.info.dbname.endswith("_test"):
                raise RuntimeError("O banco de testes precisa terminar em _test.")

    def setUp(self):
        self.connection = self.psycopg.connect(self.url, autocommit=True)
        self.addCleanup(self.connection.close)
        self.connection.execute("""
            DROP SCHEMA IF EXISTS cadastro_private CASCADE;
            DROP SCHEMA public CASCADE;
            DROP SCHEMA IF EXISTS auth CASCADE;
            CREATE SCHEMA public;
            CREATE SCHEMA auth;
            DO $$ BEGIN CREATE ROLE authenticated NOLOGIN; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
            DO $$ BEGIN CREATE ROLE anon NOLOGIN; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
            GRANT USAGE ON SCHEMA public, auth TO authenticated, anon;
            CREATE TABLE auth.users(id uuid PRIMARY KEY);
            CREATE FUNCTION auth.uid() RETURNS uuid LANGUAGE sql STABLE AS
              $$ SELECT nullif(current_setting('request.jwt.claim.sub', true), '')::uuid $$;
            CREATE FUNCTION auth.jwt() RETURNS jsonb LANGUAGE sql STABLE AS
              $$ SELECT coalesce(nullif(current_setting('request.jwt.claims', true), ''), '{}')::jsonb $$;
        """)
        self.connection.execute("INSERT INTO auth.users VALUES (%s), (%s)", (OWNER, OTHER))
        self.connection.execute((ROOT / "database/schema.sql").read_text())

    def claims(self, connection, user=OWNER, role="operator", owner=None):
        metadata = {"access_role": role}
        if owner:
            metadata["data_owner_id"] = owner
        connection.execute("SET LOCAL ROLE authenticated")
        connection.execute("SELECT set_config('request.jwt.claim.sub', %s, true), set_config('request.jwt.claims', %s, true)",
                           (user, json.dumps({"sub": user, "app_metadata": metadata})))

    def insert_product(self, connection, owner=OWNER):
        return connection.execute("INSERT INTO public.products(owner_id, name, category, price, stock) VALUES (%s, 'Caderno', 'Papelaria', 19.90, 2) RETURNING id", (owner,)).fetchone()[0]

    def test_rls_blocks_cross_account_and_anonymous_access(self):
        with self.connection.transaction():
            self.claims(self.connection)
            self.insert_product(self.connection)
            self.assertEqual(self.connection.execute("SELECT count(*) FROM public.products").fetchone()[0], 1)
        with self.connection.transaction():
            self.claims(self.connection, OTHER)
            self.assertEqual(self.connection.execute("SELECT count(*) FROM public.products").fetchone()[0], 0)
            self.assertEqual(self.connection.execute("DELETE FROM public.products RETURNING id").fetchall(), [])
            totals = self.connection.execute("SELECT public.dashboard_totals(%s)", (OTHER,)).fetchone()[0]
            self.assertEqual(totals["products"], 0)
        with self.assertRaises(self.psycopg.errors.InsufficientPrivilege), self.connection.transaction():
            self.claims(self.connection, OTHER)
            self.insert_product(self.connection, OWNER)
        with self.assertRaises(self.psycopg.errors.InsufficientPrivilege), self.connection.transaction():
            self.connection.execute("SET LOCAL ROLE anon")
            self.connection.execute("SELECT * FROM public.clients")

    def test_support_is_read_only_and_view_obeys_rls(self):
        with self.connection.transaction():
            self.claims(self.connection)
            self.connection.execute("""INSERT INTO public.clients
              (owner_id, name, city, cpf_encrypted, cpf_bindex, cpf_masked,
               email_encrypted, email_bindex, email_masked, phone_encrypted, phone_masked)
              VALUES (%s, 'Ana', 'Fortaleza', 'v1:encrypted', repeat('a',64), '012.***.***-90',
                'v1:encrypted', repeat('b',64), 'a***@***', 'v1:encrypted', '***0000')""", (OWNER,))
        with self.connection.transaction():
            self.claims(self.connection, OTHER)
            self.assertEqual(self.connection.execute("SELECT * FROM public.clients_support").fetchall(), [])
        with self.connection.transaction():
            self.claims(self.connection, OTHER, "support", OWNER)
            self.assertEqual(self.connection.execute("SELECT email FROM public.clients_support").fetchone()[0], "a***@***")
            self.assertEqual(self.connection.execute("DELETE FROM public.clients RETURNING id").fetchall(), [])
        with self.assertRaises(self.psycopg.errors.InsufficientPrivilege), self.connection.transaction():
            self.claims(self.connection, OTHER, "support", OWNER)
            self.insert_product(self.connection)

    def test_ledger_permissions_and_rollback(self):
        with self.connection.transaction():
            self.claims(self.connection)
            self.insert_product(self.connection)
        first = verify_ledger(self.connection)
        self.assertEqual(first["event_count"], 1)
        with self.assertRaises(RuntimeError), self.connection.transaction():
            self.claims(self.connection)
            self.insert_product(self.connection)
            raise RuntimeError("rollback")
        self.assertEqual(verify_ledger(self.connection), first)
        for sql in ("SELECT * FROM cadastro_private.audit_ledger", "UPDATE cadastro_private.audit_head SET last_hash=repeat('a',64)"):
            with self.assertRaises(self.psycopg.errors.InsufficientPrivilege), self.connection.transaction():
                self.claims(self.connection)
                self.connection.execute(sql)
        for sql in ("DELETE FROM cadastro_private.audit_ledger", "UPDATE cadastro_private.audit_ledger SET action='forged'", "TRUNCATE cadastro_private.audit_ledger"):
            with self.assertRaises(self.psycopg.errors.InsufficientPrivilege), self.connection.transaction():
                self.connection.execute(sql)

    def test_concurrent_writes_preserve_chain_and_external_anchor(self):
        def write(_):
            with self.psycopg.connect(self.url) as connection:
                self.claims(connection)
                self.insert_product(connection)
        with ThreadPoolExecutor(max_workers=6) as executor:
            list(executor.map(write, range(18)))
        checkpoint = verify_ledger(self.connection)
        self.assertEqual(checkpoint["event_count"], 18)
        write(None)
        self.assertEqual(verify_ledger(self.connection, checkpoint)["event_count"], 19)
        with self.assertRaises(ValueError):
            verify_ledger(self.connection, {**checkpoint, "last_hash": "f" * 64})

    def test_verifier_detects_content_tampering_and_deleted_tail(self):
        with self.connection.transaction():
            self.claims(self.connection)
            self.insert_product(self.connection)
            self.insert_product(self.connection)
        self.connection.execute("ALTER TABLE cadastro_private.audit_ledger DISABLE TRIGGER audit_no_mutation")
        self.connection.execute("UPDATE cadastro_private.audit_ledger SET action='forged' WHERE id=1")
        with self.assertRaises(ValueError):
            verify_ledger(self.connection)
        self.connection.execute("UPDATE cadastro_private.audit_ledger SET action='products.insert' WHERE id=1")
        self.assertEqual(verify_ledger(self.connection)["event_count"], 2)
        self.connection.execute("DELETE FROM cadastro_private.audit_ledger WHERE id=2")
        with self.assertRaises(ValueError):
            verify_ledger(self.connection)


if __name__ == "__main__":
    unittest.main()
