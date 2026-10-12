"""Revisa los ficheros que cambia un PR (tarea 7).

Dos reglas que ningún escáner genérico cubre:

1. Ficheros generados: cachés, entornos virtuales o artefactos de build no se
   versionan, los suba quien los suba.
2. Gobierno del agente: si algún commit del rango es del agente, el PR no puede
   tocar los ficheros que lo gobiernan (harness, workflows, Spec Kit, Dockerfile) ni
   debilitar la configuración de las comprobaciones en pyproject.toml.
   Las personas sí pueden; para ellas lo decide la revisión de Code Owners.

Uso: check_pr_files.py BASE HEAD [--agent LOGIN ...] [--pr-author LOGIN]
Escribe anotaciones de GitHub Actions y sale con 1 si encuentra algo.
"""

from __future__ import annotations

import argparse
import fnmatch
import subprocess
import sys
import tomllib

GENERATED = (
    "*.pyc", "*.pyo", "*/__pycache__/*", "__pycache__/*",
    ".venv/*", "venv/*", "*.egg-info/*", "dist/*", "build/*",
    ".pytest_cache/*", ".mypy_cache/*", ".ruff_cache/*", ".coverage",
    "*.DS_Store", ".claude/audit/*", ".claude/settings.local.json",
)
AGENT_PROTECTED = (
    ".github/", ".claude/", ".devcontainer/", ".specify/",
    "AGENTS.md", "CLAUDE.md", ".agent-standards-version",
    # Definen la imagen que se firma y se despliega (tarea 9).
    "Dockerfile", ".dockerignore",
)
# Secciones de pyproject.toml que configuran las comprobaciones de CI.
CHECK_SECTIONS = ("ruff", "mypy", "pytest", "coverage", "bandit")
DEFAULT_AGENTS = ("almagentic-agent[bot]",)


def git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def changed_files(base: str, head: str) -> list[str]:
    out = git("diff", "--name-only", "--no-renames", f"{base}...{head}")
    return [line for line in out.splitlines() if line]


def commit_authors(base: str, head: str) -> set[str]:
    out = git("log", "--format=%an%n%cn", f"{base}..{head}")
    return {line for line in out.splitlines() if line}


def is_generated(path: str) -> bool:
    return any(fnmatch.fnmatch(path, pattern) for pattern in GENERATED)


def is_agent_protected(path: str) -> bool:
    return any(path == p or path.startswith(p) for p in AGENT_PROTECTED)


def check_sections(text: str) -> dict[str, object]:
    try:
        tool = tomllib.loads(text).get("tool", {})
    except tomllib.TOMLDecodeError:
        return {"__invalid__": True}
    return {name: tool.get(name) for name in CHECK_SECTIONS}


def file_at(rev: str, path: str) -> str:
    try:
        return git("show", f"{rev}:{path}")
    except subprocess.CalledProcessError:
        return ""


def find_problems(base: str, head: str, agents: set[str], pr_author: str) -> list[tuple[str, str]]:
    files = changed_files(base, head)
    problems = [(f, "fichero generado: no debe versionarse") for f in files if is_generated(f)]
    by_agent = pr_author in agents or bool(commit_authors(base, head) & agents)
    if by_agent:
        problems += [
            (f, "el agente no puede modificar los ficheros que lo gobiernan")
            for f in files
            if is_agent_protected(f)
        ]
        if "pyproject.toml" in files:
            before = check_sections(file_at(base, "pyproject.toml"))
            after = check_sections(file_at(head, "pyproject.toml"))
            for name in CHECK_SECTIONS:
                if before.get(name) != after.get(name) or "__invalid__" in after:
                    problems.append(
                        ("pyproject.toml", f"el agente no puede cambiar la configuración [tool.{name}]")
                    )
                    break
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("base")
    parser.add_argument("head")
    parser.add_argument("--agent", action="append", default=[])
    parser.add_argument("--pr-author", default="")
    args = parser.parse_args(argv)
    agents = set(args.agent or DEFAULT_AGENTS)
    problems = find_problems(args.base, args.head, agents, args.pr_author)
    for path, message in problems:
        print(f"::error file={path}::{message}")
    if not problems:
        print("Ficheros del PR correctos.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
