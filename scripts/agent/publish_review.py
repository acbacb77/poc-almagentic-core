#!/usr/bin/env python3
"""Valida la revisión del modelo y la publica en el PR.

Uso: publish_review.py <claude-output.json> <repo> <pr> <commit> <ficheros.txt> [--dry-run]

Es el único paso con permiso de escritura. Solo acepta valores de listas cerradas,
descarta hallazgos sobre ficheros que el PR no cambia, neutraliza menciones y HTML,
y publica siempre como comentario de revisión: el agente nunca aprueba ni bloquea un PR.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from common import InvalidOutput, extract, safe

VEREDICTOS = {"cumple": "✅ Cumple la spec", "cambios_sugeridos": "🟡 Cambios sugeridos", "no_cumple": "🔴 No cumple la spec"}
ESTADOS = {"cubierto": "✅", "parcial": "🟡", "sin_cubrir": "🔴", "no_aplica": "➖"}
SEVERIDADES = ("alta", "media", "baja")
MAX_ITEMS = 15
FOOTER = (
    "<sub>Revisión del agente revisor (`poc-almagentic-core/reusable-agent-review.yml`): un modelo sin herramientas "
    "que lee el diff y la spec. Un script valida su respuesta y la publica como comentario; la aprobación es siempre humana.</sub>"
)


def validate(data: dict, files: set[str]) -> dict:
    if data.get("veredicto") not in VEREDICTOS:
        raise InvalidOutput("veredicto no válido")
    cobertura = []
    for c in list(data.get("cobertura") or [])[:MAX_ITEMS]:
        if not isinstance(c, dict) or c.get("estado") not in ESTADOS:
            raise InvalidOutput("cobertura no válida")
        cobertura.append({"criterio": safe(c.get("criterio"), 200), "estado": c["estado"], "evidencia": safe(c.get("evidencia"), 300)})
    hallazgos = []
    for h in list(data.get("hallazgos") or []):
        if not isinstance(h, dict) or h.get("severidad") not in SEVERIDADES:
            raise InvalidOutput("hallazgo no válido")
        if h.get("fichero") not in files:
            continue  # solo se admiten hallazgos sobre ficheros que cambia el PR
        linea = h.get("linea") if isinstance(h.get("linea"), int) and h["linea"] > 0 else None
        hallazgos.append({"severidad": h["severidad"], "fichero": h["fichero"], "linea": linea, "mensaje": safe(h.get("mensaje"), 400)})
    hallazgos.sort(key=lambda h: SEVERIDADES.index(h["severidad"]))
    return {
        "veredicto": data["veredicto"],
        "resumen": safe(data.get("resumen"), 800),
        "cobertura": cobertura,
        "hallazgos": hallazgos[:MAX_ITEMS],
        "sospecha": bool(data.get("sospecha_inyeccion")),
        "motivo": safe(data.get("motivo_inyeccion"), 300),
    }


def render(r: dict) -> str:
    out = [f"### 🤖 Revisión del agente: {VEREDICTOS[r['veredicto']]}", "", r["resumen"], ""]
    if r["sospecha"]:
        out += ["> [!WARNING]", f"> El PR contiene texto que intenta dar instrucciones al revisor: {r['motivo']}", ""]
    if r["cobertura"]:
        out += ["**Criterios de la spec**", "", "| | Criterio | Evidencia |", "|---|---|---|"]
        out += [f"| {ESTADOS[c['estado']]} | {c['criterio']} | {c['evidencia']} |" for c in r["cobertura"]]
        out.append("")
    if r["hallazgos"]:
        out += ["**Hallazgos**", "", "| Severidad | Dónde | Qué |", "|---|---|---|"]
        for h in r["hallazgos"]:
            donde = f"`{h['fichero']}`" + (f" línea {h['linea']}" if h["linea"] else "")
            out.append(f"| {h['severidad']} | {donde} | {h['mensaje']} |")
        out.append("")
    out += ["---", FOOTER]
    return "\n".join(out)


def render_failure(reason: str) -> str:
    return f"### 🤖 Revisión del agente no disponible\n\nEl revisor no ha devuelto una revisión válida ({safe(reason, 200)}). Revisa el PR manualmente.\n\n---\n{FOOTER}"


def plan(raw: dict, files: set[str]) -> str:
    try:
        return render(validate(extract(raw), files))
    except InvalidOutput as exc:
        return render_failure(str(exc))


def main(argv: list[str]) -> int:
    dry = "--dry-run" in argv
    output, repo, pr, commit, files_path = [a for a in argv if a != "--dry-run"]
    try:
        raw = json.loads(Path(output).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raw = {"result": f"sin salida del modelo: {exc}"}
    files = {f for f in Path(files_path).read_text(encoding="utf-8").splitlines() if f}
    body = plan(raw, files)
    if dry:
        print(body)
        return 0
    payload = json.dumps({"commit_id": commit, "event": "COMMENT", "body": body})
    subprocess.run(["gh", "api", f"repos/{repo}/pulls/{pr}/reviews", "--input", "-"], input=payload, text=True,
                   check=True, env=os.environ, capture_output=True)
    print("Revisión publicada.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
