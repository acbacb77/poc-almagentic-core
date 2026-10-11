"""Utilidades comunes de los scripts del agente revisor y del agente que responde a @claude."""

from __future__ import annotations

import json
import re
import subprocess

MAX_TEXT = 600


def git(repo: str, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", repo, *args], check=True, capture_output=True, text=True
    ).stdout


def clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit] + "\n[... recortado ...]"


def untrusted(text: str | None, limit: int) -> str:
    """Texto escrito por terceros: se recorta y no puede cerrar la etiqueta que lo envuelve."""
    s = clip(str(text or ""), limit)
    return re.sub(
        r"</?\s*(datos|instruccion|spec|diff|pr)\b",
        "[etiqueta eliminada]",
        s,
        flags=re.I,
    )


def safe(text: object, limit: int = MAX_TEXT) -> str:
    """Texto del modelo antes de publicarlo: una línea, sin HTML, sin imágenes y sin menciones."""
    s = " ".join(str(text or "").split())
    s = s.replace("<", "&lt;").replace(">", "&gt;").replace("![", "!\\[")
    s = re.sub(r"@(?=[A-Za-z0-9_-])", "@​", s)
    return s if len(s) <= limit else s[: limit - 1] + "…"


def safe_lines(text: object, limit: int = 4_000) -> str:
    """Como safe, pero conserva los saltos de línea (para descripciones de PR y comentarios largos)."""
    lines = [
        safe(line, 1_000) if line.strip() else ""
        for line in str(text or "").splitlines()
    ]
    s = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
    return s if len(s) <= limit else s[: limit - 1] + "…"


class InvalidOutput(ValueError):
    pass


def extract(raw: dict) -> dict:
    if isinstance(raw.get("structured_output"), dict):
        return raw["structured_output"]
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", str(raw.get("result") or "").strip())
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise InvalidOutput(f"la respuesta no es JSON ({exc})") from exc
    if not isinstance(data, dict):
        raise InvalidOutput("la respuesta no es un objeto JSON")
    return data
