#!/usr/bin/env python3
"""Informe de trazabilidad de una versión (tarea E).

Uso: trazabilidad.py --plan plan.json --repo owner/app --gitops owner/gitops
                     --version X.Y.Z --digest sha256:... --md salida.md --json salida.json

Para cada PR de la versión (la lista la da release.py) reconstruye la cadena completa con la
API de GitHub: de dónde salió la petición (persona o alerta), quién la aprobó y cuándo, la spec,
quién escribió el código (persona o agente, y cuántas rondas de @claude), la revisión automática,
quién aprobó el PR o si se fusionó con bypass, los checks obligatorios y la promoción a staging
que lo desplegó y quién la aprobó.

Escribe una sección Markdown para la Release y el mismo contenido en JSON como adjunto.
Solo lee: no cambia nada en GitHub.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from typing import Callable

AGENTE = "almagentic-agent[bot]"
REVISOR = "github-actions[bot]"
OBLIGATORIOS = ("ci / checks", "security / result")
CIERRA = re.compile(r"(?i)\b(?:closes|fixes|resolves|refs)\s+#(\d+)")
RAMA = re.compile(r"^(?:feat|fix|spec)/(\d+)-")
PROMOCION = re.compile(r"^deploy\(staging\): .*\(([0-9a-f]{7,40})\)\s*$")
VEREDICTO = re.compile(r"Revisión del agente:\s*(.+)")

Api = Callable[[str], object]


def gh_api(ruta: str) -> object:
    out = subprocess.run(["gh", "api", ruta], check=True, capture_output=True, text=True)
    return json.loads(out.stdout)


def fecha(f: str | None) -> str:
    return f[:16].replace("T", " ") if f else ""


def horas(a: str | None, b: str | None) -> float | None:
    if not a or not b:
        return None
    d = datetime.fromisoformat(b.replace("Z", "+00:00")) - datetime.fromisoformat(a.replace("Z", "+00:00"))
    return round(d.total_seconds() / 3600, 1)


def peticion(api: Api, repo: str, pr: dict) -> dict | None:
    m = CIERRA.search(pr.get("body") or "") or RAMA.match(pr["head"]["ref"])
    if not m:
        return None
    n = int(m.group(1))
    issue = api(f"repos/{repo}/issues/{n}")
    if "pull_request" in issue:
        return None
    eventos = api(f"repos/{repo}/issues/{n}/events?per_page=100")
    aprobado = [e for e in eventos if e.get("event") == "labeled" and e["label"]["name"] == "aprobado"]
    etiquetas = {e["name"] for e in issue.get("labels", [])}
    origen = "alerta de Prometheus" if "<!-- alerta:" in (issue.get("body") or "") else f"@{issue['user']['login']}"
    return {
        "numero": n,
        "titulo": issue["title"],
        "origen": origen,
        "creada": issue["created_at"],
        "triage": sorted(e for e in etiquetas if e.split(":")[0] in ("tipo", "prioridad", "tamano")),
        "sospechosa": "triage:sospechoso" in etiquetas,
        "aprobada_por": aprobado[0]["actor"]["login"] if aprobado else None,
        "aprobada": aprobado[0]["created_at"] if aprobado else None,
    }


def spec_de(prs_cerrados: list[dict], n: int) -> dict | None:
    specs = [p for p in prs_cerrados if p["head"]["ref"].startswith(f"spec/{n}-") and p.get("merged_at")]
    if not specs:
        return None
    p = max(specs, key=lambda x: x["merged_at"])
    return {"pr": p["number"], "autor": p["user"]["login"], "fusionada": p["merged_at"]}


def revision(api: Api, repo: str, pr: dict) -> dict:
    reviews = api(f"repos/{repo}/pulls/{pr['number']}/reviews?per_page=100")
    agente = [r for r in reviews if r["user"]["login"] == REVISOR and VEREDICTO.search(r.get("body") or "")]
    ultimo: dict[str, dict] = {}
    for r in reviews:
        if r["user"]["login"] != REVISOR and r["state"] in ("APPROVED", "CHANGES_REQUESTED", "DISMISSED"):
            ultimo[r["user"]["login"]] = r
    aprobaciones = [u for u, r in ultimo.items() if r["state"] == "APPROVED"]
    fusionado_por = (pr.get("merged_by") or {}).get("login")
    return {
        "revisor_automatico": VEREDICTO.search(agente[-1]["body"]).group(1).strip() if agente else None,
        "aprobado_por": aprobaciones,
        "fusionado_por": fusionado_por,
        # Sin aprobación vigente, el merge solo es posible saltándose el ruleset (queda auditado).
        "bypass": not aprobaciones,
    }


def autoria(api: Api, repo: str, pr: dict) -> dict:
    commits = api(f"repos/{repo}/pulls/{pr['number']}/commits?per_page=100")
    del_agente = [c for c in commits if (c.get("author") or {}).get("login") == AGENTE]
    rondas = sum(1 for c in del_agente if "cambio pedido en el PR" in c["commit"]["message"])
    return {
        "autor": pr["user"]["login"],
        "commits": len(commits),
        "commits_agente": len(del_agente),
        "rondas_claude": rondas,
        "verificados": all(c["commit"]["verification"]["verified"] for c in commits),
    }


def checks(api: Api, repo: str, sha: str) -> dict:
    runs = api(f"repos/{repo}/commits/{sha}/check-runs?per_page=100")["check_runs"]
    estado = {r["name"]: r.get("conclusion") for r in runs}
    return {n: estado.get(n, "no encontrado") for n in OBLIGATORIOS}


def despliegue(api: Api, repo: str, gitops: str, promociones: list[dict], pr: dict) -> dict | None:
    """Primera promoción fusionada después del PR cuya imagen incluye su commit."""
    for p in promociones:
        if p["merged_at"] < pr["merged_at"]:
            continue
        commit = PROMOCION.match(p["title"]).group(1)
        estado = api(f"repos/{repo}/compare/{pr['merge_commit_sha']}...{commit}").get("status")
        if estado in ("ahead", "identical"):
            # La lista de PRs no trae quién fusionó ni las revisiones: se piden aparte.
            completo = api(f"repos/{gitops}/pulls/{p['number']}")
            reviews = api(f"repos/{gitops}/pulls/{p['number']}/reviews?per_page=100")
            return {"pr": p["number"], "commit": commit, "fusionada": p["merged_at"],
                    "aprobada_por": sorted({r["user"]["login"] for r in reviews if r["state"] == "APPROVED"}),
                    "fusionada_por": (completo.get("merged_by") or {}).get("login")}
    return None


def construir(api: Api, plan: dict, repo: str, gitops: str) -> list[dict]:
    cerrados = api(f"repos/{repo}/pulls?state=closed&per_page=100")
    promos = sorted(
        (p for p in api(f"repos/{gitops}/pulls?state=closed&per_page=100")
         if p.get("merged_at") and PROMOCION.match(p["title"])),
        key=lambda p: p["merged_at"],
    )
    out = []
    for c in plan.get("cambios", []):
        pr = api(f"repos/{repo}/pulls/{c['pr']}")
        pet = peticion(api, repo, pr)
        dep = despliegue(api, repo, gitops, promos, pr)
        out.append({
            "pr": c["pr"], "titulo": pr["title"], "tipo": c["tipo"], "fusionado": pr["merged_at"],
            "peticion": pet,
            "spec": spec_de(cerrados, pet["numero"]) if pet else None,
            "autoria": autoria(api, repo, pr),
            "revision": revision(api, repo, pr),
            "checks": checks(api, repo, pr["head"]["sha"]),
            "despliegue": dep,
            "horas_peticion_a_staging": horas(pet["creada"] if pet else None, dep["fusionada"] if dep else None),
        })
    return out


def markdown(filas: list[dict], repo: str, gitops: str) -> str:
    def enlace(r: str, n: int | None) -> str:
        return f"[#{n}](https://github.com/{r}/pull/{n})" if n else "-"

    lineas = [
        "### Trazabilidad",
        "",
        "Cada cambio de esta versión, desde la petición hasta staging. Generado por "
        "`poc-almagentic-core/scripts/release/trazabilidad.py`; el detalle está en `trazabilidad.json`.",
        "",
        "| Cambio | Petición | Decisión | Spec | Código | Revisión automática | Aprobación | Checks | Staging |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for f in filas:
        p, a, r = f["peticion"], f["autoria"], f["revision"]
        pet = (f"[#{p['numero']}](https://github.com/{repo}/issues/{p['numero']}) · {p['origen']}"
               + (" ⚠️ sospechosa" if p["sospechosa"] else "")) if p else "sin issue"
        dec = f"`aprobado` por @{p['aprobada_por']} · {fecha(p['aprobada'])}" if p and p["aprobada_por"] else "-"
        spec = enlace(repo, f["spec"]["pr"]) if f["spec"] else "-"
        codigo = ("🤖 agente" if a["autor"] == AGENTE else f"@{a['autor']}")
        if a["rondas_claude"]:
            codigo += f" + {a['rondas_claude']} @claude"
        codigo += "" if a["verificados"] else " · commits sin verificar"
        rev = r["revisor_automatico"] or "-"
        if r["aprobado_por"]:
            apr = ", ".join(f"@{u}" for u in r["aprobado_por"])
        elif a["autor"] == r["fusionado_por"]:
            apr = "PR propio (GitHub no deja aprobarlo)"
        else:
            apr = f"bypass de @{r['fusionado_por']}"
        chk = " ".join("✅" if v == "success" else f"❌ {k}" for k, v in f["checks"].items())
        dep = f["despliegue"]
        if dep:
            quien = ", ".join(f"@{u}" for u in dep["aprobada_por"]) or f"bypass de @{dep['fusionada_por']}"
            stg = f"{enlace(gitops, dep['pr'])} · {quien} · {fecha(dep['fusionada'])}"
        else:
            stg = "todavía no"
        if f["horas_peticion_a_staging"] is not None:
            stg += f" · {f['horas_peticion_a_staging']} h desde la petición"
        lineas.append(f"| {enlace(repo, f['pr'])} {f['titulo'].replace('|', '/')} | {pet} | {dec} | {spec} | "
                      f"{codigo} | {rev} | {apr} | {chk} | {stg} |")
    return "\n".join(lineas) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--plan", required=True)
    p.add_argument("--repo", required=True)
    p.add_argument("--gitops", required=True)
    p.add_argument("--version", required=True)
    p.add_argument("--digest", required=True)
    p.add_argument("--md", required=True)
    p.add_argument("--json", required=True)
    a = p.parse_args(argv)
    with open(a.plan, encoding="utf-8") as f:
        plan = json.load(f)
    filas = construir(gh_api, plan, a.repo, a.gitops)
    with open(a.md, "w", encoding="utf-8") as f:
        f.write(markdown(filas, a.repo, a.gitops))
    with open(a.json, "w", encoding="utf-8") as f:
        json.dump({"version": a.version, "repo": a.repo, "imagen": a.digest, "cambios": filas},
                  f, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
