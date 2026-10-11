#!/usr/bin/env python3
"""Redacta el comentario con el que el agente responde a un @claude.

Uso: respond_report.py <estado> <claude-output.json> [--commit SHA] [--problems FICHERO] [--run URL]

Estados: pushed (cambio subido), no_changes (no ha hecho falta cambiar nada),
rejected (el cambio tocaba algo prohibido y no se ha subido), failed (el agente no terminó).
El resumen del modelo se publica neutralizado: sin HTML ni menciones.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from common import safe

TITLES = {
    "pushed": "✅ Cambio subido al PR",
    "no_changes": "ℹ️ Sin cambios en el código",
    "rejected": "⛔ Cambio no subido",
    "failed": "⚠️ No he podido completar la petición",
}
FOOTER = (
    "<sub>Respuesta del agente (`poc-almagentic-core/reusable-agent-respond.yml`). El modelo trabaja con el harness "
    "del repo y sin acceso a GitHub; un script revisa el cambio y lo sube con la identidad del agente. "
    "El merge sigue necesitando CI, seguridad y aprobación humana.</sub>"
)


def summary(output_path: str) -> str:
    try:
        raw = json.loads(Path(output_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    return safe(raw.get("result"), 1500)


def render(state: str, output_path: str, commit: str = "", problems: list[str] | None = None, run: str = "") -> str:
    out = [f"### 🤖 {TITLES[state]}", ""]
    if state == "pushed" and commit:
        out += [f"Commit: {commit}", ""]
    if state == "rejected":
        out += ["El cambio propuesto toca ficheros que el agente no puede modificar o ficheros generados:", ""]
        out += [f"- {safe(p, 300)}" for p in (problems or [])] + [""]
    text = summary(output_path)
    if text:
        out += ["**Resumen del agente**", "", text, ""]
    if state == "failed" and run:
        out += [f"Detalle en la ejecución: {run}", ""]
    out += ["---", FOOTER]
    return "\n".join(out)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("state", choices=sorted(TITLES))
    parser.add_argument("output")
    parser.add_argument("--commit", default="")
    parser.add_argument("--problems", default="")
    parser.add_argument("--run", default="")
    args = parser.parse_args(argv)
    problems = Path(args.problems).read_text(encoding="utf-8").splitlines() if args.problems else []
    sys.stdout.write(render(args.state, args.output, args.commit, [p for p in problems if p], args.run))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
