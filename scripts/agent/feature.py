#!/usr/bin/env python3
"""Utilidades del agente autónomo de features (extensión F).

Subcomandos:
  check   <fase> <issue.json> <permiso> <ramas.json>      ¿Puede el agente empezar? (sale 0 sí, 3 no y escribe el motivo)
  prompt  <fase> <instrucciones.md> <issue.json> <comentarios.json> [--spec-dir DIR]
  names   spec <issue> <ficheros.txt>                     Carpeta de la spec y rama spec/<issue>-<slug>
  names   implement <rama-de-la-spec>                     Issue, slug y rama feat/<issue>-<slug>
  scope   <fase> <ficheros.txt>                           ¿Toca el cambio solo lo que le corresponde a la fase?
  pr      <fase> <issue> <titulo-issue> <claude-output.json> <spec-dir>   Título y cuerpo del PR
  report  <estado> <claude-output.json> [--pr URL] [--reason TEXTO] [--problems FICHERO] [--run URL]

El texto del issue y de sus comentarios lo escriben terceros: va al prompt como datos.
Lo que escribe el modelo se publica neutralizado (sin HTML ni menciones).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from common import safe, safe_lines, untrusted

PHASES = ("spec", "implement")
WRITE_PERMISSIONS = {"admin", "maintain", "write"}
TRUSTED_ASSOCIATIONS = {"OWNER", "MEMBER", "COLLABORATOR"}
TRIAGE_BOT = "github-actions[bot]"
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,49}$")
SPEC_DIR = re.compile(r"^specs/(\d{3})-([a-z0-9][a-z0-9-]{0,49})/")
MAX_BODY = 6_000
MAX_COMMENT = 3_000
MAX_COMMENTS = 20


class Refused(ValueError):
    pass


# ---------- check ----------


def check(phase: str, issue: dict, permission: str, branches: list[str]) -> None:
    """Lanza Refused con el motivo si el agente no debe trabajar en este issue."""
    if phase not in PHASES:
        raise Refused(f"fase desconocida: {phase}")
    if permission not in WRITE_PERMISSIONS:
        raise Refused(
            "quien lo ha lanzado no tiene permiso de escritura en el repositorio"
        )
    if issue.get("pull_request"):
        raise Refused("es un pull request, no una petición")
    if issue.get("state") != "open":
        raise Refused("el issue está cerrado")
    labels = {lab.get("name") for lab in issue.get("labels", [])}
    if "aprobado" not in labels:
        raise Refused("el issue no tiene la etiqueta `aprobado`")
    if "triage:sospechoso" in labels:
        raise Refused(
            "el triage marcó la petición como sospechosa; quita `triage:sospechoso` si has revisado el texto"
        )
    prefix = "spec/" if phase == "spec" else "feat/"
    taken = [b for b in branches if b.startswith(f"{prefix}{issue.get('number')}-")]
    if taken:
        raise Refused(f"ya existe la rama `{taken[0]}`: el agente no repite el trabajo")


# ---------- prompt ----------


def relevant_comments(comments: list[dict]) -> list[dict]:
    """Respuestas del responsable y del triage; los comentarios de terceros no entran."""
    keep = [
        c
        for c in comments
        if c.get("association") in TRUSTED_ASSOCIATIONS or c.get("author") == TRIAGE_BOT
    ]
    return keep[-MAX_COMMENTS:]


def build_prompt(
    instructions: str, issue: dict, comments: list[dict], spec_dir: str = ""
) -> str:
    head = Path(instructions).read_text(encoding="utf-8").rstrip()
    head = head.replace("{issue}", str(int(issue["number"]))).replace(
        "{spec_dir}", spec_dir
    )
    parts = [
        head,
        f"<datos>\nIssue #{int(issue['number'])}: {untrusted(issue.get('title'), 300)}\n\n"
        f"{untrusted(issue.get('body'), MAX_BODY)}\n</datos>",
    ]
    for c in relevant_comments(comments):
        autor = untrusted(str(c.get("author") or ""), 60).replace('"', "")
        parts.append(
            f'<datos autor="{autor}">\n{untrusted(c.get("body"), MAX_COMMENT)}\n</datos>'
        )
    return "\n\n".join(parts) + "\n"


# ---------- names ----------


def spec_names(issue: int, files: list[str], added: list[str] | None = None) -> dict:
    """Carpeta y rama de la spec nueva.

    `added` son los ficheros creados (no modificados). Si se pasa, la carpeta nueva se
    busca solo entre ellos, de modo que el agente puede además retocar una spec
    existente cuando el issue lo pide (p. ej. cambiar un FR de la spec 002).
    """
    new = files if added is None else added
    dirs = {m.group(0) for f in new if (m := SPEC_DIR.match(f))}
    if len(dirs) != 1:
        raise ValueError(f"se esperaba una carpeta de spec nueva y hay {len(dirs)}")
    spec_dir = dirs.pop().rstrip("/")
    if f"{spec_dir}/spec.md" not in new:
        raise ValueError(f"falta {spec_dir}/spec.md")
    slug = SPEC_DIR.match(spec_dir + "/").group(2)
    return {
        "issue": issue,
        "slug": slug,
        "spec_dir": spec_dir,
        "branch": f"spec/{issue}-{slug}",
    }


def implement_names(spec_branch: str) -> dict:
    m = re.fullmatch(r"spec/(\d+)-(.+)", spec_branch)
    if not m or not SLUG.match(m.group(2)):
        raise ValueError(f"rama de spec no válida: {spec_branch!r}")
    issue, slug = int(m.group(1)), m.group(2)
    return {"issue": issue, "slug": slug, "branch": f"feat/{issue}-{slug}"}


# ---------- scope ----------


def out_of_scope(phase: str, files: list[str]) -> list[str]:
    """En la fase spec solo se escribe en specs/: ni código ni tests todavía."""
    if phase == "spec":
        return [f for f in files if not f.startswith("specs/")]
    return []


# ---------- pr ----------


def model_summary(output_path: str, limit: int = 4_000) -> str:
    try:
        raw = json.loads(Path(output_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    return safe_lines(raw.get("result"), limit)


FOOTER_PR = (
    "<sub>PR abierto por el agente autónomo (`poc-almagentic-core/reusable-agent-feature.yml`). "
    "El modelo trabajó con el harness del repo y sin acceso a GitHub; un script revisó el cambio y lo publicó "
    "con la identidad del agente. El merge necesita CI, seguridad y aprobación humana.</sub>"
)


def pr_text(
    phase: str, issue: int, issue_title: str, output_path: str, spec_dir: str
) -> tuple[str, str]:
    # Sin el prefijo de la plantilla de peticiones ("[Petición] ") y con mayúscula inicial.
    plain = re.sub(r"^\s*\[[^\]]{1,30}\]\s*", "", str(issue_title or "")) or str(
        issue_title or ""
    )
    title_text = safe(plain[:1].upper() + plain[1:], 80)
    if phase == "spec":
        title = f"spec: {title_text} (#{issue})"
        intro = f"Especificación de la petición #{issue} en `{spec_dir}/`, escrita por el agente con Spec Kit. No incluye código."
        link = f"Refs #{issue}"
        next_step = "Al fusionar este PR, el agente hará el plan, las tareas y la implementación en otro PR."
    else:
        title = f"feat: {title_text} (#{issue})"
        intro = f"Implementación de la petición #{issue} según `{spec_dir}/spec.md`: plan, tareas y código, escritos por el agente con Spec Kit."
        link = f"Closes #{issue}"
        next_step = "Para pedir cambios al agente, comenta `@claude` en este PR."
    summary = model_summary(output_path)
    body = [intro, ""]
    if summary:
        body += ["## Resumen del agente", "", summary, ""]
    body += [next_step, "", link, "", "---", FOOTER_PR]
    return title, "\n".join(body)


# ---------- report ----------

TITLES = {
    "opened": "✅ PR abierto",
    "refused": "ℹ️ El agente no ha empezado",
    "no_changes": "ℹ️ El agente no ha propuesto cambios",
    "rejected": "⛔ Cambio no publicado",
    "failed": "⚠️ El agente no ha podido terminar",
}
FOOTER_ISSUE = (
    "<sub>Agente autónomo (`poc-almagentic-core/reusable-agent-feature.yml`). "
    "Lo lanzan la etiqueta `aprobado` (spec) y el merge de la spec (implementación).</sub>"
)


def report(
    state: str,
    output_path: str,
    pr: str = "",
    reason: str = "",
    problems: list[str] | None = None,
    run: str = "",
) -> str:
    out = [f"### 🤖 {TITLES[state]}", ""]
    if pr:
        out += [f"PR: {pr}", ""]
    if reason:
        out += [f"Motivo: {safe(reason, 400)}", ""]
    if problems:
        out += ["El cambio propuesto toca ficheros que no le corresponden:", ""]
        out += [f"- {safe(p, 300)}" for p in problems] + [""]
    if state != "opened":
        text = model_summary(output_path, 1_500)
        if text:
            out += ["**Resumen del agente**", "", text, ""]
    if run and state in ("failed", "rejected"):
        out += [f"Detalle en la ejecución: {run}", ""]
    out += ["---", FOOTER_ISSUE]
    return "\n".join(out)


# ---------- CLI ----------


def _lines(path: str) -> list[str]:
    return [
        line.strip()
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _json(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name, args in {
        "check": ["phase", "issue", "permission", "branches"],
        "prompt": ["phase", "instructions", "issue", "comments"],
        "scope": ["phase", "files"],
        "pr": ["phase", "issue", "title", "output", "spec_dir"],
    }.items():
        p = sub.add_parser(name)
        for arg in args:
            p.add_argument(arg, type=int if (name, arg) == ("pr", "issue") else str)
    sub.choices["prompt"].add_argument("--spec-dir", default="")
    sub.choices["pr"].add_argument("--title-file", required=True)
    sub.choices["pr"].add_argument("--body-file", required=True)
    p = sub.add_parser("names")
    p.add_argument("phase")
    p.add_argument("args", nargs="+")
    p = sub.add_parser("report")
    p.add_argument("state", choices=sorted(TITLES))
    p.add_argument("output")
    for opt in ("--pr", "--reason", "--problems", "--run"):
        p.add_argument(opt, default="")
    a = parser.parse_args(argv)

    if a.cmd == "check":
        try:
            check(a.phase, _json(a.issue), a.permission.strip(), _json(a.branches))
        except Refused as exc:
            print(exc)
            return 3
        return 0
    if a.cmd == "prompt":
        sys.stdout.write(
            build_prompt(a.instructions, _json(a.issue), _json(a.comments), a.spec_dir)
        )
        return 0
    if a.cmd == "names":
        names = (
            spec_names(
                int(a.args[0]),
                _lines(a.args[1]),
                _lines(a.args[2]) if len(a.args) > 2 else None,
            )
            if a.phase == "spec"
            else implement_names(a.args[0])
        )
        for k, v in names.items():
            print(f"{k.replace('_', '-')}={v}")
        return 0
    if a.cmd == "scope":
        bad = out_of_scope(a.phase, _lines(a.files))
        for f in bad:
            print(f"{f}: en la fase spec solo se escribe en specs/")
        return 1 if bad else 0
    if a.cmd == "pr":
        title, body = pr_text(a.phase, a.issue, a.title, a.output, a.spec_dir)
        Path(a.title_file).write_text(title, encoding="utf-8")
        Path(a.body_file).write_text(body, encoding="utf-8")
        return 0
    problems = _lines(a.problems) if a.problems else []
    sys.stdout.write(report(a.state, a.output, a.pr, a.reason, problems, a.run))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
