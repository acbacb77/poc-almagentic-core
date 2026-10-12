import pytest

from base_images import InvalidDockerfile, base_images

D = "sha256:" + "a" * 64


def test_detecta_imagenes_y_etapas():
    text = f"""
FROM ghcr.io/astral-sh/uv:0.11.32@{D} AS uv
FROM python:3.12-slim AS build
COPY --from=uv /uv /bin/uv
FROM build AS test
FROM --platform=linux/amd64 python:3.12-slim@{D}
"""
    assert base_images(text) == [
        (f"ghcr.io/astral-sh/uv:0.11.32@{D}", True),
        ("python:3.12-slim", False),
        (f"python:3.12-slim@{D}", True),
    ]


def test_scratch_no_es_imagen_base():
    assert base_images(f"FROM python@{D} AS b\nFROM scratch\n") == [(f"python@{D}", True)]


def test_digest_incompleto_no_cuenta_como_fijado():
    assert base_images("FROM python:3.12@sha256:abc\n") == [("python:3.12@sha256:abc", False)]


@pytest.mark.parametrize("text", ["FROM ${BASE}\n", "FROM $BASE AS x\n", "RUN echo\n", "FROM\n"])
def test_rechaza(text):
    with pytest.raises(InvalidDockerfile):
        base_images(text)


def test_lineas_partidas():
    assert base_images(f"FROM \\\n  python:3.12@{D}\n") == [(f"python:3.12@{D}", True)]
