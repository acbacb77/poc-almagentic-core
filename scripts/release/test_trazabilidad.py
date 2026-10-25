import trazabilidad as t

APP, GITOPS = "o/app", "o/gitops"


def pr(n, ref, autor="almagentic-agent[bot]", body="", merged="2026-10-25T10:00:00Z", title=None, by="persona"):
    return {"number": n, "title": title or f"feat: cosa (#{n})", "body": body, "head": {"ref": ref, "sha": f"h{n}"},
            "user": {"login": autor}, "merged_at": merged, "merge_commit_sha": f"m{n}",
            "merged_by": {"login": by}}


def commit(autor, msg, verificado=True):
    return {"author": {"login": autor}, "commit": {"message": msg, "verification": {"verified": verificado}}}


def review(user, state, body=""):
    return {"user": {"login": user}, "state": state, "body": body}


def fake():
    feat = pr(38, "feat/36-v2", body="Closes #36")
    spec = pr(37, "spec/36-v2", merged="2026-10-25T09:00:00Z")
    deps = pr(34, "dependabot/uv/x", autor="dependabot[bot]", title="deps: bump")
    promo_vieja = {"number": 20, "title": "deploy(staging): app sha256:1 (aaaaaaa)", "merged_at": "2026-10-25T09:30:00Z"}
    promo = {"number": 21, "title": "deploy(staging): app sha256:2 (bbbbbbb)", "merged_at": "2026-10-25T11:00:00Z"}
    datos = {
        f"repos/{APP}/pulls?state=closed&per_page=100": [feat, spec, deps],
        f"repos/{GITOPS}/pulls?state=closed&per_page=100": [promo, promo_vieja, {"number": 5, "title": "fix", "merged_at": "x"}],
        f"repos/{APP}/pulls/38": feat,
        f"repos/{APP}/pulls/34": deps,
        f"repos/{APP}/issues/36": {"number": 36, "title": "[Petición] v2", "user": {"login": "persona"},
                                   "created_at": "2026-10-25T08:00:00Z", "body": "texto",
                                   "labels": [{"name": "tipo:funcionalidad"}, {"name": "aprobado"}]},
        f"repos/{APP}/issues/36/events?per_page=100": [
            {"event": "labeled", "label": {"name": "tipo:funcionalidad"}, "actor": {"login": "github-actions[bot]"}},
            {"event": "labeled", "label": {"name": "aprobado"}, "actor": {"login": "persona"},
             "created_at": "2026-10-25T08:30:00Z"}],
        f"repos/{APP}/pulls/38/reviews?per_page=100": [
            review("github-actions[bot]", "COMMENTED", "### 🤖 Revisión del agente: ✅ Cumple la spec\n..."),
            review("persona", "APPROVED")],
        f"repos/{APP}/pulls/34/reviews?per_page=100": [review("persona", "APPROVED"), review("persona", "DISMISSED")],
        f"repos/{APP}/pulls/38/commits?per_page=100": [commit("almagentic-agent[bot]", "feat: x"),
                                                      commit("almagentic-agent[bot]", "chore(agent): cambio pedido en el PR #38")],
        f"repos/{APP}/pulls/34/commits?per_page=100": [commit("dependabot[bot]", "deps: bump", verificado=False)],
        f"repos/{APP}/commits/h38/check-runs?per_page=100": {"check_runs": [
            {"name": "ci / checks", "conclusion": "success"}, {"name": "security / result", "conclusion": "success"}]},
        f"repos/{APP}/commits/h34/check-runs?per_page=100": {"check_runs": [
            {"name": "ci / checks", "conclusion": "failure"}]},
        f"repos/{APP}/compare/m38...aaaaaaa": {"status": "behind"},
        f"repos/{APP}/compare/m38...bbbbbbb": {"status": "ahead"},
        f"repos/{APP}/compare/m34...bbbbbbb": {"status": "ahead"},
        f"repos/{GITOPS}/pulls/21": {"merged_by": {"login": "persona"}},
        f"repos/{GITOPS}/pulls/21/reviews?per_page=100": [review("persona", "APPROVED")],
    }
    return datos.__getitem__


PLAN = {"cambios": [{"pr": 38, "tipo": "feat", "descripcion": "v2", "agente": True},
                    {"pr": 34, "tipo": "deps", "descripcion": "bump", "agente": True}]}


def test_cadena_completa_de_un_cambio_del_agente():
    f = t.construir(fake(), PLAN, APP, GITOPS)[0]
    assert f["peticion"]["numero"] == 36 and f["peticion"]["aprobada_por"] == "persona"
    assert f["peticion"]["triage"] == ["tipo:funcionalidad"]
    assert f["spec"]["pr"] == 37
    assert f["autoria"] == {"autor": "almagentic-agent[bot]", "commits": 2, "commits_agente": 2,
                            "rondas_claude": 1, "verificados": True}
    assert f["revision"]["revisor_automatico"] == "✅ Cumple la spec"
    assert f["revision"]["aprobado_por"] == ["persona"] and not f["revision"]["bypass"]
    assert f["checks"] == {"ci / checks": "success", "security / result": "success"}
    # La promoción anterior al merge no cuenta; la siguiente que contiene el commit, sí.
    assert f["despliegue"]["pr"] == 21 and f["despliegue"]["aprobada_por"] == ["persona"]
    assert f["horas_peticion_a_staging"] == 3.0


def test_aprobacion_descartada_cuenta_como_bypass_y_sin_issue():
    f = t.construir(fake(), PLAN, APP, GITOPS)[1]
    assert f["peticion"] is None and f["spec"] is None
    assert f["revision"]["aprobado_por"] == [] and f["revision"]["bypass"]
    assert f["checks"]["security / result"] == "no encontrado"
    assert not f["autoria"]["verificados"]


def test_markdown():
    md = t.markdown(t.construir(fake(), PLAN, APP, GITOPS), APP, GITOPS)
    assert "| Cambio | Petición | Decisión |" in md
    assert "[#36](https://github.com/o/app/issues/36) · @persona" in md
    assert "🤖 agente + 1 @claude" in md
    assert "bypass de @persona" in md
    assert "❌ ci / checks" in md and "commits sin verificar" in md
    assert "3.0 h desde la petición" in md


def test_peticion_de_una_alerta():
    api = fake()

    def con_alerta(ruta):
        r = api(ruta)
        if ruta.endswith("issues/36"):
            r = {**r, "body": "...\n<!-- alerta:BusquedasRechazadas -->"}
        return r

    f = t.construir(con_alerta, {"cambios": PLAN["cambios"][:1]}, APP, GITOPS)[0]
    assert f["peticion"]["origen"] == "alerta de Prometheus"
