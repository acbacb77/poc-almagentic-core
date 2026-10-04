#!/usr/bin/env python3
"""Construye el prompt del agente de triage.

Uso: build_prompt.py <instrucciones.md> <issue.json> <abiertos.json> > prompt.md

El contenido del issue es de un usuario y no es confiable: aquí solo se
recorta y se envuelve en etiquetas; nunca pasa por la shell ni por
expresiones ${{ }} del workflow.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

MAX_TITLE = 300
MAX_BODY = 20_000
MAX_CANDIDATES = 100


def clean(text: str | None, limit: int) -> str:
    text = (text or "").replace("\r\n", "\n")
    # Evita que el usuario cierre nuestras etiquetas y "salga" del bloque de datos.
    for tag in ("peticion", "issues_abiertos"):
        text = text.replace(f"</{tag}>", f"<\\/{tag}>")
    if len(text) > limit:
        text = text[:limit] + "\n[… recortado …]"
    return text


def main(instructions: str, issue_path: str, open_path: str) -> str:
    issue = json.loads(Path(issue_path).read_text(encoding="utf-8"))
    candidates = json.loads(Path(open_path).read_text(encoding="utf-8"))
    number = issue["number"]
    others = [c for c in candidates if c.get("number") != number][:MAX_CANDIDATES]
    others_txt = "\n".join(f"#{c['number']}: {clean(c.get('title'), MAX_TITLE)}" for c in others)
    schema = Path(__file__).with_name("schema.json").read_text(encoding="utf-8")
    return (
        Path(instructions).read_text(encoding="utf-8")
        + "\n## Esquema JSON de la respuesta\n\n```json\n" + schema + "```\n"
        + f"\n<peticion numero=\"{number}\">\n"
        + f"Título: {clean(issue.get('title'), MAX_TITLE)}\n\n"
        + clean(issue.get("body"), MAX_BODY)
        + "\n</peticion>\n\n<issues_abiertos>\n"
        + (others_txt or "(ninguno)")
        + "\n</issues_abiertos>\n\n"
        + "Devuelve solo el objeto JSON.\n"
    )


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    sys.stdout.write(main(*sys.argv[1:]))
