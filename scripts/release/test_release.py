import json

import pytest

from release import main, next_version, parse, plan


def rec(subject, body="", author="persona"):
    return f"abc123\x1f{author}\x1f{subject}\x1f{body}\x1e"


SQUASH = rec(
    "feat: buscar productos (#18) (#20)",
    "* feat\n\nCo-authored-by: almagentic-agent[bot] <x@y>",
)
MERGE = rec(
    "Merge pull request #21 from o/feat/promote",
    "feat(promote): promoción verificada\n",
)
FIX = rec("fix(deps): certifi 2026.10.23 (PYSEC-2026-4320) (#25)")
DOCS = rec("docs: cierre de la tarea 9 (#20)")
SPEC = rec("spec: [Petición] buscar productos (#18) (#19)")
BOT = rec("feat: catálogo de productos (#10)", "", "almagentic-agent[bot]")


def test_squash_toma_el_ultimo_numero_como_pr_y_detecta_al_agente():
    (c,) = parse(SQUASH)
    assert (c.type, c.desc, c.pr, c.agent) == (
        "feat",
        "buscar productos (#18)",
        "20",
        True,
    )


def test_merge_commit_toma_el_titulo_del_cuerpo():
    (c,) = parse(MERGE)
    assert (c.type, c.scope, c.desc, c.pr, c.agent) == (
        "feat",
        "promote",
        "promoción verificada",
        "21",
        False,
    )


@pytest.mark.parametrize(
    ("log", "bump"),
    [
        (DOCS + SPEC, "none"),
        (DOCS + FIX, "patch"),
        (FIX + SQUASH, "minor"),
        (FIX + rec("feat(api)!: quitar /v1 (#30)"), "major"),
        (rec("refactor: x (#1)", "BREAKING CHANGE: adiós"), "major"),
        (rec("ci: algo (#2)"), "patch"),
        (rec("Actualizar README"), "none"),
    ],
)
def test_bump(log, bump):
    assert plan(log, "v1.7.2", "1.0.0", "o/r")["bump"] == bump


@pytest.mark.parametrize(
    ("last", "bump", "expected"),
    [
        ("v1.7.2", "patch", "1.7.3"),
        ("v1.7.2", "minor", "1.8.0"),
        ("v1.7.2", "major", "2.0.0"),
        ("", "minor", "1.0.0"),
    ],
)
def test_next_version(last, bump, expected):
    assert next_version(last, bump, "1.0.0") == expected


def test_next_version_rechaza_etiquetas_raras():
    with pytest.raises(ValueError):
        next_version("v1", "patch", "1.0.0")


def test_notas():
    r = plan(SQUASH + FIX + DOCS + SPEC, "v1.0.0", "1.0.0", "o/r", "2026-10-24")
    n = r["notes"]
    assert r["version"] == "1.1.0" and n.startswith("## v1.1.0 (2026-10-24)")
    assert (
        "### Novedades\n\n- buscar productos (#18) ([#20](https://github.com/o/r/pull/20)) 🤖"
        in n
    )
    assert "### Correcciones\n\n- **deps:** certifi" in n
    assert "Además, 2 cambio(s)" in n and "🤖 = cambio con commits del agente" in n
    assert "compare/v1.0.0...v1.1.0" in n


def test_sin_cambios_publicables():
    assert plan(DOCS, "v1.0.0", "1.0.0", "o/r") == {
        "bump": "none",
        "version": "1.0.0",
        "notes": "",
    }


def test_main(monkeypatch, capsys):
    import io

    monkeypatch.setattr("sys.stdin", io.StringIO(FIX))
    assert main(["--last-tag", "v1.7.2", "--repo", "o/r"]) == 0
    assert json.loads(capsys.readouterr().out)["version"] == "1.7.3"


def test_autor_bot_y_prefijo_de_plantilla():
    (c,) = parse(BOT)
    assert c.agent
    (s,) = parse(rec("feat: [Petición] buscar productos (#18) (#20)"))
    assert s.desc == "buscar productos (#18)"


def test_mensajes_sin_conventional_commits_no_se_listan():
    n = plan(FIX + rec("Initial commit"), "v1.0.0", "1.0.0", "o/r")["notes"]
    assert "Initial commit" not in n and "Además, 1 cambio(s)" in n
