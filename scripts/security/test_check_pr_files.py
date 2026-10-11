import subprocess
from pathlib import Path

import pytest

import check_pr_files as c

AGENT = "almagentic-agent[bot]"
PYPROJECT = '[project]\nname = "x"\ndependencies = []\n\n[tool.ruff]\nline-length = 100\n'


def run(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True).stdout


@pytest.fixture
def repo(tmp_path, monkeypatch):
    run(tmp_path, "init", "-q", "-b", "main")
    (tmp_path / "pyproject.toml").write_text(PYPROJECT)
    (tmp_path / "app.py").write_text("x = 1\n")
    run(tmp_path, "add", ".")
    commit(tmp_path, "humano", "base")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def commit(repo: Path, author: str, msg: str) -> str:
    run(repo, "-c", f"user.name={author}", "-c", "user.email=a@b.c", "commit", "-q", "-m", msg)
    return run(repo, "rev-parse", "HEAD").strip()


def change(repo: Path, author: str, files: dict[str, str]) -> tuple[str, str]:
    base = run(repo, "rev-parse", "HEAD").strip()
    for name, content in files.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    run(repo, "add", "-f", ".")
    return base, commit(repo, author, "cambio")


def problems(base, head, author=""):
    return c.find_problems(base, head, {AGENT}, author)


def test_cambio_normal_del_agente_pasa(repo):
    base, head = change(repo, AGENT, {"app.py": "x = 2\n", "specs/001/spec.md": "spec"})
    assert problems(base, head) == []


@pytest.mark.parametrize("path", ["src/__pycache__/m.cpython-312.pyc", "m.pyc", ".venv/bin/python",
                                  "pkg.egg-info/PKG-INFO", ".pytest_cache/v/x", ".claude/audit/denials.jsonl"])
def test_ficheros_generados_fallan_aunque_los_suba_una_persona(repo, path):
    base, head = change(repo, "humano", {path: "x"})
    assert [p for p, _ in problems(base, head)] == [path]


@pytest.mark.parametrize("path", [".github/workflows/ci.yml", ".claude/settings.json", ".specify/templates/spec-template.md",
                                  ".devcontainer/devcontainer.json", "AGENTS.md", "CLAUDE.md", ".agent-standards-version"])
def test_el_agente_no_toca_ficheros_protegidos(repo, path):
    base, head = change(repo, AGENT, {path: "x"})
    assert [p for p, _ in problems(base, head)] == [path]


def test_una_persona_si_puede_tocar_ficheros_protegidos(repo):
    base, head = change(repo, "humano", {"AGENTS.md": "x", ".specify/templates/t.md": "y"})
    assert problems(base, head) == []


def test_se_detecta_al_agente_por_el_autor_del_pr(repo):
    base, head = change(repo, "humano", {"CLAUDE.md": "x"})
    assert problems(base, head, author=AGENT)


def test_el_agente_puede_cambiar_dependencias(repo):
    nuevo = PYPROJECT.replace("dependencies = []", 'dependencies = ["fastapi"]')
    base, head = change(repo, AGENT, {"pyproject.toml": nuevo})
    assert problems(base, head) == []


@pytest.mark.parametrize("nuevo", [
    PYPROJECT.replace("line-length = 100", "line-length = 100\nextend-exclude = [\"src\"]"),
    PYPROJECT + "\n[tool.mypy]\nignore_errors = true\n",
    PYPROJECT + "\n[tool.pytest.ini_options]\naddopts = \"-k not_slow\"\n",
])
def test_el_agente_no_debilita_la_configuracion_de_las_comprobaciones(repo, nuevo):
    base, head = change(repo, AGENT, {"pyproject.toml": nuevo})
    assert problems(base, head) == [("pyproject.toml", problems(base, head)[0][1])]


def test_main_devuelve_1_y_anota_el_fichero(repo, capsys):
    base, head = change(repo, AGENT, {".github/workflows/x.yml": "x"})
    assert c.main([base, head]) == 1
    assert "::error file=.github/workflows/x.yml::" in capsys.readouterr().out
