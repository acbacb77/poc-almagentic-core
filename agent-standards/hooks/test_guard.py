"""Tests del guardarraíl. Ejecutar: python3 -m pytest agent-standards/hooks -q"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

GUARD = Path(__file__).with_name("guard.py")


def run(tool, tool_input, project):
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(project)}
    out = subprocess.run(
        [sys.executable, str(GUARD)],
        input=json.dumps({"tool_name": tool, "tool_input": tool_input}),
        capture_output=True, text=True, env=env, check=True,
    ).stdout
    return json.loads(out)["hookSpecificOutput"]["permissionDecision"] if out else "pass"


@pytest.fixture
def project(tmp_path):
    return tmp_path


BLOCKED_BASH = [
    "git push origin main",
    "git push origin HEAD:main",
    "git push origin +feat/x:refs/heads/main",
    "git push --force origin feat/x",
    "git push -f",
    "git config user.name hacker",
    "git -c credential.helper= push origin feat/x",
    "git commit --no-verify -m x",
    "gh pr merge 3 --squash",
    "gh api repos/acbacb77/poc-almagentic-app",
    "gh auth status",
    "cat /run/secrets/agent.pem",
    "openssl rsa -in key.pem",
    "cat .env",
    "echo 'x' > .github/workflows/ci.yml",
    "sed -i 's/a/b/' AGENTS.md",
    "rm -rf .claude/hooks",
    "cp evil.json .claude/settings.json",
    "uv run pytest && git push origin main",
    "mv CLAUDE.md /tmp/x",
    "cat AGENTS.md > CLAUDE.md",
]
ALLOWED_BASH = [
    "git push origin feat/12-hello",
    "git push -u origin fix/3-bug",
    "git commit -m 'feat: hola' -m 'Refs #12'",
    "uv run pytest -q",
    "cat AGENTS.md",
    "grep -n deny .claude/settings.json",
    "git diff .github/workflows/ci.yml",
    "gh pr create --fill",
    "pip download --index-url https://api.github.com/x pkg",
    "ls specs/001-hello",
]


@pytest.mark.parametrize("command", BLOCKED_BASH)
def test_bash_blocked(command, project):
    assert run("Bash", {"command": command}, project) == "deny"


@pytest.mark.parametrize("command", ALLOWED_BASH)
def test_bash_allowed(command, project):
    assert run("Bash", {"command": command}, project) == "pass"


@pytest.mark.parametrize("path", [".github/workflows/ci.yml", "AGENTS.md", ".claude/settings.json",
                                  ".devcontainer/devcontainer.json", ".specify/memory/constitution.md"])
def test_edit_protected_blocked(path, project):
    assert run("Edit", {"file_path": str(project / path)}, project) == "deny"
    assert run("Write", {"file_path": path}, project) == "deny"


@pytest.mark.parametrize("path", ["src/app/main.py", "tests/test_main.py", "specs/001-x/spec.md"])
def test_edit_code_allowed(path, project):
    assert run("Edit", {"file_path": str(project / path)}, project) == "pass"


@pytest.mark.parametrize("path", ["/run/secrets/agent.pem", "keys/app.pem", ".env", "config/.env.prod"])
def test_read_secret_blocked(path, project):
    assert run("Read", {"file_path": path}, project) == "deny"


def test_read_protected_allowed(project):
    assert run("Read", {"file_path": str(project / "AGENTS.md")}, project) == "pass"


def test_denial_is_audited(project):
    run("Bash", {"command": "git push origin main"}, project)
    log = (project / ".claude/audit/denials.jsonl").read_text().splitlines()
    assert json.loads(log[-1])["reason"] == "push a la rama protegida main"
