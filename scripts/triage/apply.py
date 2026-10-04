#!/usr/bin/env python3
"""Valida la propuesta del agente de triage y la aplica al issue.

Uso: apply.py <claude-output.json> <issue> <abiertos.json> [--dry-run]

Este paso es determinista y es el único con permiso de escritura: el modelo
no puede añadir etiquetas ni comentar por sí mismo. Solo se aceptan valores
de listas cerradas, los textos se recortan y se neutralizan menciones y HTML,
y las referencias a otros issues se validan contra los issues abiertos reales.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

ENUMS = {
    "tipo": ["funcionalidad", "mejora", "bug", "retirada", "pregunta"],
    "prioridad": ["alta", "media", "baja"],
    "tamano": ["S", "M", "L", "XL"],
}
LIMITS = {"criterios_aceptacion": 6, "preguntas_abiertas": 5, "riesgos": 5, "relacionados": 5}
MAX_TEXT = 500
LABELS = {
    "tipo:funcionalidad": ("1d76db", "Algo nuevo"),
    "tipo:mejora": ("5319e7", "Cambio en algo existente"),
    "tipo:bug": ("d73a4a", "Algo no funciona"),
    "tipo:retirada": ("6a737d", "Eliminar o deprecar algo"),
    "tipo:pregunta": ("cfd3d7", "No es trabajo de desarrollo"),
    "prioridad:alta": ("b60205", "Prioridad alta"),
    "prioridad:media": ("fbca04", "Prioridad media"),
    "prioridad:baja": ("0e8a16", "Prioridad baja"),
    "tamano:S": ("c2e0c6", "Horas"),
    "tamano:M": ("bfdadc", "1-2 días"),
    "tamano:L": ("fef2c0", "Una semana"),
    "tamano:XL": ("f9d0c4", "Hay que dividirla"),
    "triage:pendiente": ("ededed", "Pendiente de triage"),
    "triage:propuesto": ("0052cc", "El agente ha propuesto un triage; falta la decisión humana"),
    "triage:manual": ("e99695", "Requiere triage humano"),
    "triage:sospechoso": ("b60205", "Posible prompt injection: revisar con cuidado"),
    "triage:repetir": ("ededed", "Volver a lanzar el triage"),
    "aprobado": ("0e8a16", "Aprobado por un responsable: listo para la spec"),
}
FOOTER = (
    "<sub>Propuesta generada por el agente de triage "
    "(`poc-almagentic-core/reusable-triage.yml`), un modelo sin herramientas ni permisos de escritura. "
    "Las etiquetas y este comentario los aplica un script que valida su respuesta.</sub>"
)


class InvalidProposal(ValueError):
    pass


def extract(raw: dict) -> dict:
    if isinstance(raw.get("structured_output"), dict):
        return raw["structured_output"]
    text = str(raw.get("result") or "").strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise InvalidProposal(f"la respuesta no es JSON ({exc})") from exc
    if not isinstance(data, dict):
        raise InvalidProposal("la respuesta no es un objeto JSON")
    return data


def safe(text: object, limit: int = MAX_TEXT) -> str:
    s = " ".join(str(text or "").split())
    s = s.replace("<", "&lt;").replace(">", "&gt;")
    s = s.replace("![", "!\\[")
    s = re.sub(r"@(?=[A-Za-z0-9_-])", "@​", s)
    return s if len(s) <= limit else s[: limit - 1] + "…"


def validate(data: dict, issue: int, open_numbers: set[int]) -> dict:
    out: dict = {}
    for field, allowed in ENUMS.items():
        if data.get(field) not in allowed:
            raise InvalidProposal(f"{field} no válido: {data.get(field)!r}")
        out[field] = data[field]
    for field in ("resumen", "valor"):
        out[field] = safe(data.get(field))
        if not out[field]:
            raise InvalidProposal(f"{field} vacío")
    for field in ("criterios_aceptacion", "preguntas_abiertas", "riesgos"):
        items = data.get(field) or []
        if not isinstance(items, list):
            raise InvalidProposal(f"{field} no es una lista")
        out[field] = [safe(i, 300) for i in items if str(i).strip()][: LIMITS[field]]
    candidates = open_numbers - {issue}
    dup = data.get("duplicado_de")
    out["duplicado_de"] = dup if isinstance(dup, int) and dup in candidates else None
    rel = data.get("relacionados") or []
    out["relacionados"] = sorted({r for r in rel if isinstance(r, int) and r in candidates})[: LIMITS["relacionados"]]
    out["sospecha_inyeccion"] = data.get("sospecha_inyeccion") is True
    out["motivo_inyeccion"] = safe(data.get("motivo_inyeccion")) if out["sospecha_inyeccion"] else ""
    return out


def render(p: dict) -> str:
    lines = ["### 🤖 Propuesta de triage", ""]
    if p["sospecha_inyeccion"]:
        lines += [
            "> [!WARNING]",
            "> **Posible prompt injection.** El texto de la petición parece contener instrucciones dirigidas al agente. "
            "Revísala con cuidado antes de aprobarla.",
            f"> Motivo: {p['motivo_inyeccion']}",
            "",
        ]
    lines += [
        "> [!NOTE]",
        "> Esto es una **propuesta**. Si estás de acuerdo, un responsable añade la etiqueta `aprobado` "
        "y el agente redactará la spec. Si no, cambia las etiquetas o comenta qué falta.",
        "",
        f"**Resumen:** {p['resumen']}",
        "",
        "| Tipo | Prioridad | Tamaño |",
        "|---|---|---|",
        f"| `{p['tipo']}` | `{p['prioridad']}` | `{p['tamano']}` |",
        "",
        f"**Valor:** {p['valor']}",
        "",
    ]
    if p["criterios_aceptacion"]:
        lines += ["**Criterios de aceptación propuestos**", ""]
        lines += [f"- [ ] {c}" for c in p["criterios_aceptacion"]] + [""]
    if p["preguntas_abiertas"]:
        lines += ["**Preguntas abiertas**", ""] + [f"- {q}" for q in p["preguntas_abiertas"]] + [""]
    if p["duplicado_de"]:
        lines += [f"**Posible duplicado de:** #{p['duplicado_de']}", ""]
    if p["relacionados"]:
        lines += ["**Relacionados:** " + ", ".join(f"#{r}" for r in p["relacionados"]), ""]
    if p["riesgos"]:
        lines += ["**Riesgos**", ""] + [f"- {r}" for r in p["riesgos"]] + [""]
    lines += ["---", FOOTER]
    return "\n".join(lines) + "\n"


def render_failure(reason: str) -> str:
    return (
        "### 🤖 Triage no disponible\n\n"
        "El agente no ha devuelto una propuesta válida, así que esta petición queda para **triage manual**.\n\n"
        f"Detalle técnico: {safe(reason, 200)}\n\n---\n{FOOTER}\n"
    )


def plan(raw: dict, issue: int, open_numbers: set[int]) -> tuple[list[str], list[str], str]:
    remove = ["triage:pendiente", "triage:repetir", "triage:propuesto", "triage:manual"]
    try:
        p = validate(extract(raw), issue, open_numbers)
    except InvalidProposal as exc:
        return ["triage:manual"], remove, render_failure(str(exc))
    add = [f"tipo:{p['tipo']}", f"prioridad:{p['prioridad']}", f"tamano:{p['tamano']}", "triage:propuesto"]
    if p["sospecha_inyeccion"]:
        add.append("triage:sospechoso")
    return add, [r for r in remove if r not in add], render(p)


def gh(*args: str, stdin: str | None = None) -> None:
    subprocess.run(["gh", *args], input=stdin, text=True, check=True)


def apply(repo: str, issue: int, add: list[str], remove: list[str], body: str) -> None:
    for name in add:
        color, desc = LABELS[name]
        gh("label", "create", name, "--repo", repo, "--color", color, "--description", desc, "--force")
    current = subprocess.run(
        ["gh", "issue", "view", str(issue), "--repo", repo, "--json", "labels", "--jq", ".labels[].name"],
        text=True, capture_output=True, check=True,
    ).stdout.split("\n")
    stale = [lbl for lbl in current if lbl.startswith(("tipo:", "prioridad:", "tamano:")) and lbl not in add]
    to_remove = [lbl for lbl in remove + stale if lbl in current]
    args = ["issue", "edit", str(issue), "--repo", repo, "--add-label", ",".join(add)]
    if to_remove:
        args += ["--remove-label", ",".join(to_remove)]
    gh(*args)
    gh("issue", "comment", str(issue), "--repo", repo, "--body-file", "-", stdin=body)


def main(argv: list[str]) -> int:
    dry = "--dry-run" in argv
    args = [a for a in argv if a != "--dry-run"]
    if len(args) != 3:
        sys.exit(__doc__)
    out_path, issue_s, open_path = args
    issue = int(issue_s)
    try:
        raw = json.loads(Path(out_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raw = {"result": f"(sin salida del agente: {exc})"}
    open_numbers = {c["number"] for c in json.loads(Path(open_path).read_text(encoding="utf-8"))}
    add, remove, body = plan(raw, issue, open_numbers)
    if dry:
        print(json.dumps({"add": add, "remove": remove}, ensure_ascii=False))
        print(body)
        return 0
    apply(os.environ["REPO"], issue, add, remove, body)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
