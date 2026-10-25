#!/usr/bin/env python3
"""Evals del harness de los agentes sin herramientas: triage y revisor (tarea C).

Uso:
  run_evals.py --model MODELO --out DIR [--casos evals] [--agente triage|revisor]
               [--repeticiones N] [--min-acierto 0.9] [--respuestas DIR]

Cada caso de `evals/<agente>/` es una entrada fija (un issue, o un repo con un PR) y lo
que se espera de la respuesta. El script construye el prompt con los mismos scripts que
usan los workflows reales, llama al modelo con las mismas opciones (sin herramientas,
salida JSON con esquema) y pasa la respuesta por el mismo validador que decide qué se
publica. Así se evalúa la cadena completa, no solo el modelo.

Sirve para decidir si se puede cambiar de modelo: se lanza con el modelo nuevo y se
compara el informe con el del modelo actual.

Con --respuestas no se llama al modelo: se leen respuestas guardadas
(<agente>-<caso>-<n>.json). Lo usan los tests y permite repetir la puntuación.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

CORE = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(CORE / "scripts" / "triage"), str(CORE / "scripts" / "agent")]

import apply as triage_apply  # noqa: E402
import build_prompt as triage_prompt  # noqa: E402
import common  # noqa: E402
import publish_review  # noqa: E402
import review_prompt  # noqa: E402

AGENTES = ("triage", "revisor")
SEVERIDADES = ("alta", "media", "baja")


@dataclass
class Resultado:
    agente: str
    caso: str
    repeticion: int
    comprobaciones: list[tuple[str, bool, str]] = field(default_factory=list)
    error: str = ""
    turnos: int | None = None
    coste: float | None = None
    duracion_ms: int | None = None

    @property
    def ok(self) -> bool:
        return not self.error and all(c[1] for c in self.comprobaciones)


# ---------- casos ----------


def cargar_casos(carpeta: Path, agente: str) -> list[dict]:
    casos = []
    for f in sorted((carpeta / agente).glob("*.json")):
        caso = json.loads(f.read_text(encoding="utf-8"))
        caso.setdefault("id", f.stem)
        casos.append(caso)
    return casos


def repo_del_caso(caso: dict, destino: Path) -> tuple[str, str, set[str]]:
    """Crea un repo git con el estado base y el del PR. Devuelve base, head y ficheros."""

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(destino), *args],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    def escribir(ficheros: dict[str, str | None]) -> None:
        for ruta, contenido in ficheros.items():
            p = destino / ruta
            if contenido is None:
                p.unlink(missing_ok=True)
                continue
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(contenido, encoding="utf-8")

    destino.mkdir(parents=True, exist_ok=True)
    git("init", "-q", "-b", "main")
    git("config", "user.email", "evals@example.invalid")
    git("config", "user.name", "evals")
    escribir(caso["repo"]["base"])
    git("add", "-A")
    git("commit", "-q", "-m", "base")
    base = git("rev-parse", "HEAD")
    escribir(caso["repo"]["pr"])
    git("add", "-A")
    git("commit", "-q", "-m", "pr")
    head = git("rev-parse", "HEAD")
    ficheros = set(git("diff", "--name-only", f"{base}...{head}").splitlines())
    return base, head, ficheros


def prompt_triage(caso: dict, tmp: Path) -> str:
    (tmp / "issue.json").write_text(json.dumps(caso["issue"]), encoding="utf-8")
    (tmp / "abiertos.json").write_text(
        json.dumps(caso.get("abiertos", [])), encoding="utf-8"
    )
    return triage_prompt.main(
        str(CORE / "prompts" / "triage.md"),
        str(tmp / "issue.json"),
        str(tmp / "abiertos.json"),
    )


# ---------- modelo ----------


def llamar_modelo(prompt: str, modelo: str, esquema: Path, cwd: Path) -> dict:
    """Mismas opciones que reusable-triage.yml y reusable-agent-review.yml."""
    proc = subprocess.run(
        [
            "claude",
            "-p",
            prompt,
            "--model",
            modelo,
            "--tools",
            "",
            "--disallowedTools",
            "mcp__*",
            "--max-turns",
            "3",
            "--no-session-persistence",
            "--output-format",
            "json",
            "--json-schema",
            esquema.read_text(encoding="utf-8"),
        ],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"is_error": True, "result": (proc.stderr or proc.stdout)[-500:]}


# ---------- puntuación ----------


def puntuar_triage(propuesta: dict, esperado: dict) -> list[tuple[str, bool, str]]:
    out = []
    for campo in ("tipo", "prioridad", "tamano"):
        if campo in esperado:
            valor = propuesta[campo]
            out.append(
                (
                    campo,
                    valor in esperado[campo],
                    f"{valor} (se acepta {', '.join(esperado[campo])})",
                )
            )
    if "sospecha_inyeccion" in esperado:
        valor = propuesta["sospecha_inyeccion"]
        out.append(
            (
                "sospecha de inyección",
                valor == esperado["sospecha_inyeccion"],
                str(valor).lower(),
            )
        )
    if "referencia" in esperado:
        n = esperado["referencia"]
        refs = (
            [propuesta["duplicado_de"]] if propuesta["duplicado_de"] else []
        ) + propuesta["relacionados"]
        out.append(
            (
                f"referencia a #{n}",
                n in refs,
                ", ".join(f"#{r}" for r in refs) or "ninguna",
            )
        )
    if "min_preguntas" in esperado:
        n = len(propuesta["preguntas_abiertas"])
        out.append(
            (
                "preguntas abiertas",
                n >= esperado["min_preguntas"],
                f"{n} (mínimo {esperado['min_preguntas']})",
            )
        )
    return out


def puntuar_revisor(revision: dict, esperado: dict) -> list[tuple[str, bool, str]]:
    out = []
    if "veredicto" in esperado:
        v = revision["veredicto"]
        out.append(
            (
                "veredicto",
                v in esperado["veredicto"],
                f"{v} (se acepta {', '.join(esperado['veredicto'])})",
            )
        )
    if "sospecha_inyeccion" in esperado:
        v = revision["sospecha"]
        out.append(
            (
                "sospecha de inyección",
                v == esperado["sospecha_inyeccion"],
                str(v).lower(),
            )
        )
    if "hallazgo" in esperado:
        h = esperado["hallazgo"]
        palabras = [p.lower() for p in h.get("palabras", [])]
        encontrados = [
            x
            for x in revision["hallazgos"]
            if x["fichero"] == h["fichero"]
            and x["severidad"] in h.get("severidades", SEVERIDADES)
            and (not palabras or any(p in x["mensaje"].lower() for p in palabras))
        ]
        detalle = (
            "; ".join(f"{x['severidad']} {x['fichero']}" for x in revision["hallazgos"])
            or "sin hallazgos"
        )
        out.append((f"hallazgo en {h['fichero']}", bool(encontrados), detalle))
    if "max_severidad" in esperado:
        limite = SEVERIDADES.index(esperado["max_severidad"])
        peores = [
            x["severidad"]
            for x in revision["hallazgos"]
            if SEVERIDADES.index(x["severidad"]) < limite
        ]
        out.append(("sin hallazgos graves", not peores, ", ".join(peores) or "ninguno"))
    return out


def evaluar(
    agente: str, caso: dict, salida: dict, ficheros: set[str] | None = None
) -> list[tuple[str, bool, str]]:
    """Valida la salida con el validador real y la compara con lo esperado."""
    if agente == "triage":
        datos = triage_apply.extract(salida)
        numeros = {i["number"] for i in caso.get("abiertos", [])} | {
            caso["issue"]["number"]
        }
        propuesta = triage_apply.validate(datos, caso["issue"]["number"], numeros)
        return puntuar_triage(propuesta, caso["esperado"])
    datos = common.extract(salida)
    revision = publish_review.validate(datos, ficheros or set())
    return puntuar_revisor(revision, caso["esperado"])


# ---------- ejecución ----------


def ejecutar(args: argparse.Namespace) -> list[Resultado]:
    resultados = []
    agentes = [args.agente] if args.agente else list(AGENTES)
    for agente in agentes:
        esquema = CORE / (
            "scripts/triage/schema.json"
            if agente == "triage"
            else "scripts/agent/review_schema.json"
        )
        for caso in cargar_casos(Path(args.casos), agente):
            with tempfile.TemporaryDirectory() as t:
                tmp = Path(t)
                ficheros = None
                if agente == "triage":
                    prompt = prompt_triage(caso, tmp)
                else:
                    base, head, ficheros = repo_del_caso(caso, tmp / "repo")
                    prompt = review_prompt.build(
                        str(CORE / "prompts" / "review.md"),
                        str(tmp / "repo"),
                        base,
                        head,
                        caso["pr"],
                        caso.get("comentarios", []),
                    )
                vacio = tmp / "vacio"
                vacio.mkdir()
                for n in range(1, args.repeticiones + 1):
                    nombre = f"{agente}-{caso['id']}-{n}.json"
                    if args.respuestas:
                        salida = json.loads(
                            (Path(args.respuestas) / nombre).read_text(encoding="utf-8")
                        )
                    else:
                        inicio = time.monotonic()
                        salida = llamar_modelo(prompt, args.model, esquema, vacio)
                        salida.setdefault(
                            "duration_ms", int((time.monotonic() - inicio) * 1000)
                        )
                    Path(args.out, nombre).write_text(
                        json.dumps(salida, ensure_ascii=False), encoding="utf-8"
                    )
                    r = Resultado(
                        agente,
                        caso["id"],
                        n,
                        turnos=salida.get("num_turns"),
                        coste=salida.get("total_cost_usd"),
                        duracion_ms=salida.get("duration_ms"),
                    )
                    try:
                        if salida.get("is_error"):
                            raise ValueError(
                                f"el modelo devolvió un error: {str(salida.get('result'))[:200]}"
                            )
                        r.comprobaciones = evaluar(agente, caso, salida, ficheros)
                    except (
                        ValueError
                    ) as exc:  # InvalidProposal e InvalidOutput heredan de ValueError
                        r.error = str(exc)
                    resultados.append(r)
                    print(
                        f"{'✅' if r.ok else '❌'} {agente}/{caso['id']} #{n}",
                        file=sys.stderr,
                    )
    return resultados


def informe(resultados: list[Resultado], modelo: str, casos: dict[str, str]) -> str:
    total = len(resultados)
    aciertos = sum(r.ok for r in resultados)
    costes = [r.coste for r in resultados if r.coste is not None]
    duraciones = [r.duracion_ms for r in resultados if r.duracion_ms]
    lineas = [
        f"## Evals del harness · `{modelo}`",
        "",
        f"**Acierto: {aciertos}/{total} ({aciertos / total:.0%})**"
        if total
        else "Sin casos.",
        "",
        "| Agente | Aciertos | Coste equivalente (USD) | Duración media |",
        "|---|---|---|---|",
    ]
    for agente in AGENTES:
        rs = [r for r in resultados if r.agente == agente]
        if not rs:
            continue
        c = sum(r.coste or 0 for r in rs)
        d = [r.duracion_ms for r in rs if r.duracion_ms]
        media = f"{sum(d) / len(d) / 1000:.1f} s" if d else "-"
        lineas.append(
            f"| {agente} | {sum(r.ok for r in rs)}/{len(rs)} | {c:.4f} | {media} |"
        )
    lineas += [
        "",
        "| Caso | Qué prueba | Rep. | Resultado | Detalle |",
        "|---|---|---|---|---|",
    ]
    for r in resultados:
        if r.error:
            detalle = f"respuesta rechazada: {r.error}"
        else:
            detalle = "; ".join(
                f"{'✓' if ok else '✗'} {n}: {d}" for n, ok, d in r.comprobaciones
            )
        detalle = detalle.replace("|", "\\|")
        lineas.append(
            f"| {r.agente}/{r.caso} | {casos.get(f'{r.agente}/{r.caso}', '')} | {r.repeticion} | "
            f"{'✅' if r.ok else '❌'} | {detalle} |"
        )
    lineas += [
        "",
        f"Coste total equivalente: {sum(costes):.4f} USD (con suscripción no se cobra). "
        f"Duración total: {sum(duraciones) / 1000:.0f} s.",
    ]
    return "\n".join(lineas) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--model", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--casos", default=str(CORE / "evals"))
    p.add_argument("--agente", choices=AGENTES)
    p.add_argument("--repeticiones", type=int, default=1)
    p.add_argument("--min-acierto", type=float, default=1.0)
    p.add_argument("--respuestas", default="")
    args = p.parse_args(argv)
    Path(args.out).mkdir(parents=True, exist_ok=True)

    resultados = ejecutar(args)
    casos = {
        f"{a}/{c['id']}": c.get("descripcion", "")
        for a in AGENTES
        for c in cargar_casos(Path(args.casos), a)
    }
    texto = informe(resultados, args.model, casos)
    Path(args.out, "informe.md").write_text(texto, encoding="utf-8")
    Path(args.out, "resultados.json").write_text(
        json.dumps(
            [
                {
                    "agente": r.agente,
                    "caso": r.caso,
                    "repeticion": r.repeticion,
                    "ok": r.ok,
                    "error": r.error,
                    "comprobaciones": r.comprobaciones,
                    "turnos": r.turnos,
                    "coste": r.coste,
                    "duracion_ms": r.duracion_ms,
                }
                for r in resultados
            ],
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )
    sys.stdout.write(texto)
    acierto = sum(r.ok for r in resultados) / len(resultados) if resultados else 0.0
    if acierto < args.min_acierto:
        print(
            f"::error title=Evals por debajo del umbral::{acierto:.0%} < {args.min_acierto:.0%}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
