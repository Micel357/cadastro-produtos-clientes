"""Preenche chaves ausentes em .env sem imprimi-las nem substituir chaves existentes."""

import base64
import os
from pathlib import Path

root = Path(__file__).resolve().parents[1]
target = root / ".env"
content = target.read_text() if target.exists() else (root / "config/.env.example").read_text()
lines = content.splitlines()
for name in ("DATA_ENCRYPTION_KEY", "BLIND_INDEX_SECRET"):
    matches = [i for i, line in enumerate(lines) if line.startswith(name + "=")]
    if len(matches) > 1:
        raise SystemExit(f"Remova definições duplicadas de {name} antes de continuar.")
    if matches and lines[matches[0]].split("=", 1)[1].strip():
        continue
    value = name + "=" + base64.b64encode(os.urandom(32)).decode()
    if matches:
        lines[matches[0]] = value
    else:
        lines.append(value)
descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
with os.fdopen(descriptor, "w") as output:
    output.write("\n".join(lines) + "\n")
target.chmod(0o600)
print("Chaves configuradas em .env. Guarde uma cópia segura fora do repositório.")
