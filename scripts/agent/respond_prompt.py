#!/usr/bin/env python3
"""Prepara el prompt del agente que atiende un comentario @claude en un PR.

Uso: respond_prompt.py <instrucciones.md> <comentario.json> <pr.json>

El comentario lo escribe una persona con permiso de escritura (lo comprueba el
workflow antes de llegar aquí): es la petición. El título y la descripción del PR
son contexto y van marcados como datos.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from common import untrusted

MAX_COMMENT = 4_000
MAX_BODY = 5_000


def build(instructions: str, comment: dict, pr: dict) -> str:
    autor = untrusted(str(comment.get("author") or ""), 60).replace('"', "")
    parts = [
        Path(instructions).read_text(encoding="utf-8").rstrip(),
        f'<instruccion autor="{autor}">\n{untrusted(comment.get("body"), MAX_COMMENT)}\n</instruccion>',
        f"<datos>\nPR: {untrusted(pr.get('title'), 300)}\nRama: {untrusted(pr.get('headRefName'), 200)}\n\n"
        f"{untrusted(pr.get('body'), MAX_BODY)}\n</datos>",
    ]
    return "\n\n".join(parts) + "\n"


def main(argv: list[str]) -> int:
    instructions, comment_path, pr_path = argv
    comment = json.loads(Path(comment_path).read_text(encoding="utf-8"))
    pr = json.loads(Path(pr_path).read_text(encoding="utf-8"))
    sys.stdout.write(build(instructions, comment, pr))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
