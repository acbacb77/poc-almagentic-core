#!/usr/bin/env python3
"""Prepara el prompt del agente revisor.

Uso: review_prompt.py <instrucciones.md> <repo> <base> <head> <pr.json> [comentarios.json]

Junta el diff del PR, las specs que afecta y el título y la descripción del PR.
Todo lo que viene del PR va envuelto como datos: el revisor no tiene herramientas
y su respuesta la valida otro script antes de publicarse.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from common import git, untrusted

MAX_DIFF = 60_000
MAX_SPEC = 20_000
MAX_BODY = 5_000
MAX_DECISION = 2_000
MAX_DECISIONES = 10
# Solo cuentan como decisiones los comentarios de quien puede aprobar el PR.
RESPONSABLES = {"OWNER", "MEMBER", "COLLABORATOR"}


def decisiones(comentarios: list[dict]) -> list[dict]:
    """Comentarios del PR escritos por responsables (no bots), los más recientes."""
    utiles = [
        c
        for c in comentarios
        if c.get("author_association") in RESPONSABLES
        and not str((c.get("user") or {}).get("login", "")).endswith("[bot]")
    ]
    return utiles[-MAX_DECISIONES:]


def specs_for(repo: str, files: list[str]) -> list[str]:
    touched = sorted(
        {m.group(1) for f in files if (m := re.match(r"(specs/[^/]+)/", f))}
    )
    if not touched:
        touched = sorted(
            str(p.parent.relative_to(repo)) for p in Path(repo).glob("specs/*/spec.md")
        )
    return [d for d in touched if (Path(repo) / d / "spec.md").is_file()]


def build(
    instructions: str,
    repo: str,
    base: str,
    head: str,
    pr: dict,
    comentarios: list[dict] | None = None,
) -> str:
    files = [
        f
        for f in git(repo, "diff", "--name-only", f"{base}...{head}").splitlines()
        if f
    ]
    diff = git(
        repo, "diff", "--unified=3", f"{base}...{head}", "--", ".", ":(exclude)uv.lock"
    )
    parts = [Path(instructions).read_text(encoding="utf-8").rstrip(), ""]
    parts.append(
        f"<pr>\nTítulo: {untrusted(pr.get('title'), 300)}\n\n{untrusted(pr.get('body'), MAX_BODY)}\n</pr>"
    )
    for d in specs_for(repo, files):
        text = (Path(repo) / d / "spec.md").read_text(encoding="utf-8")
        parts.append(f'<spec ruta="{d}/spec.md">\n{untrusted(text, MAX_SPEC)}\n</spec>')
    elegidos = decisiones(comentarios or [])
    if elegidos:
        texto = "\n\n".join(
            f"@{c['user']['login']} ({c['author_association']}, {str(c.get('created_at', ''))[:16]}):\n"
            f"{untrusted(c.get('body'), MAX_DECISION)}"
            for c in elegidos
        )
        parts.append(f"<decisiones>\n{texto}\n</decisiones>")
    parts.append("<ficheros>\n" + "\n".join(files) + "\n</ficheros>")
    parts.append(f"<diff>\n{untrusted(diff, MAX_DIFF)}\n</diff>")
    return "\n\n".join(parts) + "\n"


def main(argv: list[str]) -> int:
    instructions, repo, base, head, pr_path, *resto = argv
    pr = json.loads(Path(pr_path).read_text(encoding="utf-8"))
    comentarios = (
        json.loads(Path(resto[0]).read_text(encoding="utf-8")) if resto else []
    )
    sys.stdout.write(build(instructions, repo, base, head, pr, comentarios))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
