"""Verifica o ledger sob um snapshot consistente e, opcionalmente, uma âncora externa."""

import argparse
import hashlib
import json
import os
from pathlib import Path


def verify_ledger(connection, checkpoint: dict | None = None) -> dict:
    previous = "0" * 64
    count = 0
    last_id = 0
    checkpoint_found = checkpoint is None or checkpoint == {"last_id": 0, "event_count": 0, "last_hash": previous}
    with connection.transaction():
        connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        with connection.cursor(name="audit_verification") as cursor:
            cursor.execute("""
                SELECT id, previous_hash, current_hash,
                  cadastro_private.audit_payload(id, occurred_at, actor, action, details, previous_hash)
                FROM cadastro_private.audit_ledger ORDER BY id
            """)
            for event_id, prior_hash, current_hash, payload in cursor:
                if event_id <= last_id or prior_hash != previous:
                    raise ValueError(f"Encadeamento inválido no evento {event_id}.")
                if hashlib.sha256(payload.encode("utf-8")).hexdigest() != current_hash:
                    raise ValueError(f"Conteúdo adulterado no evento {event_id}.")
                count += 1
                last_id, previous = event_id, current_hash
                if checkpoint and event_id == checkpoint["last_id"]:
                    checkpoint_found = current_hash == checkpoint["last_hash"] and count == checkpoint["event_count"]
        head = connection.execute("SELECT last_id, event_count, last_hash FROM cadastro_private.audit_head WHERE singleton").fetchone()
        if head != (last_id, count, previous):
            raise ValueError("Cabeçalho divergente: eventos ausentes ou cauda removida.")
        if not checkpoint_found:
            raise ValueError("O ledger diverge da âncora externa.")
    return {"last_id": last_id, "event_count": count, "last_hash": previous}


def main() -> None:
    import psycopg

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, help="Âncora de uma verificação anterior, guardada fora do banco.")
    args = parser.parse_args()
    checkpoint = json.loads(args.checkpoint.read_text()) if args.checkpoint else None
    # A senha nunca vai na linha de comando. A CA do provedor deve estar em PGSSLROOTCERT.
    try:
        with psycopg.connect(os.environ["AUDIT_DATABASE_URL"], sslmode="verify-full", autocommit=True) as connection:
            result = verify_ledger(connection, checkpoint)
    except (KeyError, ValueError, psycopg.Error) as error:
        # Erros de conexão do driver podem conter informações do endpoint: não imprime DSN.
        raise SystemExit(f"Verificação falhou ({type(error).__name__}). Revise a conexão ou a integridade.") from None
    print(json.dumps(result))


if __name__ == "__main__":
    main()
