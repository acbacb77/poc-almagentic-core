#!/usr/bin/env python3
"""Guardarraíl PreToolUse para Claude Code (agent-standards v1.0.0).

Segunda capa de defensa, por detrás de las reglas de permisos de settings.json.
Bloquea lo que una regla de permisos puede no ver: rutas protegidas escritas
desde Bash, push a main por refspec, lectura de claves, etc.

Cada bloqueo se registra en .claude/audit/denials.jsonl para la trazabilidad.
No es la última barrera: detrás están la GitHub App sin permiso Workflows,
CODEOWNERS y la protección de la rama main.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import shlex
import sys
from pathlib import Path

PROTECTED = (
    ".github/",
    ".claude/",
    ".devcontainer/",
    ".specify/memory/",
    "AGENTS.md",
    "CLAUDE.md",
    ".agent-standards-version",
)
PROTECTED_IN_COMMAND = {
    p: re.compile(r"(?:^|[\s'\"=>/])(?:\./)?" + re.escape(p.rstrip("/")) + r"(?=/|\s|['\"]|$)")
    for p in PROTECTED
}
SECRET_PATTERNS = (
    re.compile(r"(^|/)\.env(\.[^/]*)?$"),
    re.compile(r"\.pem$"),
    re.compile(r"^/run/secrets(/|$)"),
)
SECRET_IN_COMMAND = re.compile(r"/run/secrets|\.pem\b|(^|[\s/])\.env(\.\w+)?\b")
READ_ONLY_COMMANDS = {
    "cat", "less", "head", "tail", "grep", "rg", "ls", "wc", "diff", "stat", "file",
}
READ_ONLY_GIT = {"diff", "log", "show", "status", "blame"}
SEPARATORS = re.compile(r"\|\||&&|[;|&\n]")
PROTECTED_BRANCHES = {"main", "master"}


def project_dir() -> Path:
    return Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())).resolve()


def relative(path_str: str) -> str:
    path = Path(path_str)
    if not path.is_absolute():
        path = project_dir() / path
    try:
        return path.resolve().relative_to(project_dir()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def is_protected(rel: str) -> bool:
    return any(rel == p.rstrip("/") or rel.startswith(p) for p in PROTECTED)


def is_secret(path_str: str) -> bool:
    candidates = {path_str, relative(path_str), Path(path_str).resolve().as_posix()}
    return any(p.search(c) for p in SECRET_PATTERNS for c in candidates)


def check_file_tool(tool: str, tool_input: dict) -> str | None:
    path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    if not path:
        return None
    if is_secret(path):
        return f"acceso a un secreto ({path})"
    if tool != "Read" and is_protected(relative(path)):
        return f"modificación de un fichero protegido ({relative(path)})"
    return None


def git_push_problem(words: list[str]) -> str | None:
    args = words[2:]
    if any(a in ("-f", "--force", "--mirror") or a.startswith("--force") for a in args):
        return "force push"
    for arg in args:
        target = arg.split(":")[-1].lstrip("+")
        target = target.removeprefix("refs/heads/")
        if target in PROTECTED_BRANCHES:
            return f"push a la rama protegida {target}"
    return None


def check_subcommand(sub: str) -> str | None:
    try:
        words = shlex.split(sub)
    except ValueError:
        words = sub.split()
    while words and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", words[0]):
        words = words[1:]
    if not words:
        return None
    cmd = os.path.basename(words[0])
    if SECRET_IN_COMMAND.search(sub):
        return "el comando referencia un secreto"
    if cmd == "git" and len(words) > 1:
        verb = words[1]
        if verb in ("config", "-c") or any(w.startswith("-c") and len(w) > 2 for w in words[1:2]):
            return "cambio de configuración de git"
        if verb == "push":
            return git_push_problem(words)
        if verb == "commit" and "--no-verify" in words:
            return "commit saltándose las comprobaciones (--no-verify)"
    if cmd == "gh" and len(words) > 1:
        if words[1] in ("api", "auth", "secret", "repo"):
            return f"gh {words[1]} no está permitido al agente"
        if words[1] == "pr" and len(words) > 2 and words[2] == "merge":
            return "el agente no fusiona PRs"
    touches_protected = [p for p in PROTECTED if PROTECTED_IN_COMMAND[p].search(sub)]
    if touches_protected:
        read_only = cmd in READ_ONLY_COMMANDS or (
            cmd == "git" and len(words) > 1 and words[1] in READ_ONLY_GIT
        )
        has_redirect = re.search(r"(^|[^0-9&])>{1,2}", sub) is not None
        if not read_only or has_redirect:
            return f"el comando puede modificar un fichero protegido ({touches_protected[0]})"
    return None


def check_bash(tool_input: dict) -> str | None:
    command = tool_input.get("command", "")
    for sub in SEPARATORS.split(command):
        problem = check_subcommand(sub.strip())
        if problem:
            return problem
    return None


def audit(tool: str, reason: str, detail: str) -> None:
    try:
        log_dir = project_dir() / ".claude" / "audit"
        log_dir.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "tool": tool,
            "reason": reason,
            "detail": detail[:500],
        }
        with (log_dir / "denials.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    tool = event.get("tool_name", "")
    tool_input = event.get("tool_input") or {}
    if tool == "Bash":
        reason = check_bash(tool_input)
        detail = tool_input.get("command", "")
    elif tool in ("Edit", "Write", "NotebookEdit", "Read"):
        reason = check_file_tool(tool, tool_input)
        detail = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    else:
        return 0
    if not reason:
        return 0
    audit(tool, reason, detail)
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    f"Bloqueado por el guardarraíl de agent-standards: {reason}. "
                    "Si crees que el cambio es necesario, explícalo en el issue o en el PR "
                    "para que lo haga un humano."
                ),
            }
        },
        sys.stdout,
        ensure_ascii=False,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
