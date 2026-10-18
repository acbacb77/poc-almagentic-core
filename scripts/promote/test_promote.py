import pytest

from promote import PromoteError, images, main, set_digest

A = "sha256:" + "a" * 64
B = "sha256:" + "b" * 64
KUST = f"""apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: staging
resources:
  - deployment.yaml
images:
  - name: ghcr.io/o/otra
    digest: {B}
  - name: ghcr.io/o/app
    digest: {A}
"""


def test_images_detecta_fijadas_y_sin_fijar():
    rendered = f"""
spec:
  containers:
    - name: api
      image: ghcr.io/o/app@{A}
    - image: "busybox:1.36"
  initContainers:
  - image: ghcr.io/o/app@{A}
"""
    assert images(rendered) == [(f"ghcr.io/o/app@{A}", True), ("busybox:1.36", False)]


def test_digest_corto_no_cuenta():
    assert images("image: x@sha256:abc\n") == [("x@sha256:abc", False)]


def test_set_cambia_solo_la_imagen_pedida():
    new, old = set_digest(KUST, "ghcr.io/o/app", B)
    assert old == A
    assert new.count(B) == 2 and A not in new
    assert new.index("ghcr.io/o/otra") < new.index(f"digest: {B}")


@pytest.mark.parametrize(
    ("image", "digest", "msg"),
    [
        ("ghcr.io/o/nada", B, "no está"),
        ("ghcr.io/o/app", "sha256:corto", "no válido"),
    ],
)
def test_set_errores(image, digest, msg):
    with pytest.raises(PromoteError, match=msg):
        set_digest(KUST, image, digest)


def test_set_sin_linea_digest():
    with pytest.raises(PromoteError, match="digest"):
        set_digest("images:\n  - name: x\n    newTag: v1\n", "x", A)


def test_main_set_devuelve_3_si_no_cambia(tmp_path, capsys):
    k = tmp_path / "kustomization.yaml"
    k.write_text(KUST)
    assert main(["set", str(k), "ghcr.io/o/app", A]) == 3
    assert main(["set", str(k), "ghcr.io/o/app", B]) == 0
    assert capsys.readouterr().out.split() == [A, A]
    assert f"digest: {B}" in k.read_text()
