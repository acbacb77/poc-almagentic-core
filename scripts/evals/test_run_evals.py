import json
from pathlib import Path

import pytest

import run_evals as ev

CASOS = Path(__file__).resolve().parents[2] / "evals"


def triage_ok(**cambios):
    datos = {
        "tipo": "funcionalidad",
        "prioridad": "media",
        "tamano": "M",
        "resumen": "Filtrar por precio",
        "valor": "Encontrar antes",
        "criterios_aceptacion": ["a"],
        "preguntas_abiertas": ["¿moneda?"],
        "duplicado_de": None,
        "relacionados": [],
        "riesgos": [],
        "sospecha_inyeccion": False,
        "motivo_inyeccion": "",
    }
    datos.update(cambios)
    return {
        "structured_output": datos,
        "num_turns": 2,
        "total_cost_usd": 0.01,
        "duration_ms": 3000,
    }


def revision(veredicto="no_cumple", hallazgos=None, sospecha=False):
    return {
        "structured_output": {
            "veredicto": veredicto,
            "resumen": "r",
            "cobertura": [],
            "hallazgos": hallazgos or [],
            "sospecha_inyeccion": sospecha,
            "motivo_inyeccion": "",
        }
    }


@pytest.mark.parametrize("agente", ev.AGENTES)
def test_los_casos_estan_bien_formados(agente):
    casos = ev.cargar_casos(CASOS, agente)
    assert len(casos) >= 5
    for c in casos:
        assert c["descripcion"] and c["esperado"]
        assert ("issue" in c) if agente == "triage" else ("repo" in c and "pr" in c)


def test_triage_acierta_y_falla_por_campo():
    caso = json.loads((CASOS / "triage/funcionalidad.json").read_text(encoding="utf-8"))
    assert all(ok for _, ok, _ in ev.evaluar("triage", caso, triage_ok()))
    fallos = [
        n
        for n, ok, _ in ev.evaluar(
            "triage", caso, triage_ok(tipo="bug", preguntas_abiertas=[])
        )
        if not ok
    ]
    assert fallos == ["tipo", "preguntas abiertas"]


def test_triage_referencia_solo_a_issues_reales():
    caso = json.loads((CASOS / "triage/duplicado.json").read_text(encoding="utf-8"))
    assert all(
        ok for _, ok, _ in ev.evaluar("triage", caso, triage_ok(duplicado_de=40))
    )
    # Un número que no está entre los abiertos lo descarta el validador real.
    assert not all(
        ok for _, ok, _ in ev.evaluar("triage", caso, triage_ok(duplicado_de=99))
    )


def test_triage_respuesta_invalida_es_error():
    caso = json.loads((CASOS / "triage/bug.json").read_text(encoding="utf-8"))
    with pytest.raises(ValueError):
        ev.evaluar("triage", caso, triage_ok(tipo="urgente"))


def test_repo_del_caso_y_hallazgo(tmp_path):
    caso = json.loads((CASOS / "revisor/fuga-log.json").read_text(encoding="utf-8"))
    base, head, ficheros = ev.repo_del_caso(caso, tmp_path / "repo")
    assert base != head and ficheros == {
        "src/app/busqueda.py",
        "tests/test_busqueda.py",
    }
    bien = revision(
        hallazgos=[
            {
                "severidad": "alta",
                "fichero": "src/app/busqueda.py",
                "linea": 17,
                "mensaje": "Registra el texto de q en el log (FR-011)",
            }
        ]
    )
    assert all(ok for _, ok, _ in ev.evaluar("revisor", caso, bien, ficheros))
    # Un hallazgo sobre un fichero que el PR no toca lo descarta el validador real.
    fuera = revision(
        hallazgos=[
            {
                "severidad": "alta",
                "fichero": "src/app/otro.py",
                "linea": 1,
                "mensaje": "log con el texto",
            }
        ]
    )
    assert not all(ok for _, ok, _ in ev.evaluar("revisor", caso, fuera, ficheros))


def test_revisor_max_severidad():
    assert (
        ev.puntuar_revisor(
            {
                "veredicto": "cumple",
                "sospecha": False,
                "hallazgos": [{"severidad": "alta", "fichero": "a", "mensaje": ""}],
            },
            {"max_severidad": "media"},
        )[0][1]
        is False
    )


def test_ejecucion_completa_con_respuestas_guardadas(tmp_path, capsys):
    resp = tmp_path / "resp"
    resp.mkdir()
    for c in ev.cargar_casos(CASOS, "triage"):
        datos = triage_ok()
        if c["id"] == "bug":
            datos = triage_ok(tipo="bug")
        (resp / f"triage-{c['id']}-1.json").write_text(
            json.dumps(datos), encoding="utf-8"
        )
    code = ev.main(
        [
            "--model",
            "fake",
            "--out",
            str(tmp_path / "out"),
            "--agente",
            "triage",
            "--respuestas",
            str(resp),
            "--min-acierto",
            "0.2",
        ]
    )
    informe = (tmp_path / "out" / "informe.md").read_text(encoding="utf-8")
    assert code == 0 and "## Evals del harness · `fake`" in informe
    assert "| triage/bug |" in informe and "✅" in informe and "❌" in informe
    assert (
        ev.main(
            [
                "--model",
                "fake",
                "--out",
                str(tmp_path / "out2"),
                "--agente",
                "triage",
                "--respuestas",
                str(resp),
            ]
        )
        == 1
    )
