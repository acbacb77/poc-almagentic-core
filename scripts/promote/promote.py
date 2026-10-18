#!/usr/bin/env python3
"""Utilidades de la promoción a gitops (tarea 10).

  images                        Lee manifiestos renderizados (kubectl kustomize) por la entrada
                                estándar e imprime cada imagen con `fijada` o `sin-fijar`.
  set <kustomization> <imagen> <digest>
                                Cambia el digest de esa imagen en el bloque `images:` de una
                                kustomization. Imprime el digest anterior. Sale con 3 si ya era ese.

En gitops solo se despliega por digest: una etiqueta puede moverse y el digest no.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

IMAGE = re.compile(r"""^\s*(?:-\s+)?image:\s*["']?([^\s"'#]+)""", re.M)
DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
PINNED = re.compile(r"@sha256:[0-9a-f]{64}$")


class PromoteError(ValueError):
    pass


def images(rendered: str) -> list[tuple[str, bool]]:
    seen: dict[str, bool] = {}
    for ref in IMAGE.findall(rendered):
        seen.setdefault(ref, bool(PINNED.search(ref)))
    return list(seen.items())


def set_digest(text: str, image: str, digest: str) -> tuple[str, str]:
    """Devuelve (texto nuevo, digest anterior)."""
    if not DIGEST.match(digest):
        raise PromoteError(f"digest no válido: {digest}")
    lines = text.splitlines(keepends=True)
    in_images = False
    for i, line in enumerate(lines):
        if re.match(r"^images:\s*$", line):
            in_images = True
            continue
        if in_images and re.match(r"^\S", line):
            break
        m = re.match(r"^(\s*)-\s+name:\s*(\S+)\s*$", line) if in_images else None
        if not m or m.group(2) != image:
            continue
        for j in range(i + 1, len(lines)):
            if re.match(r"^\s*-\s", lines[j]) or re.match(r"^\S", lines[j]):
                break
            d = re.match(r"^(\s*)digest:\s*(\S+)\s*$", lines[j])
            if d:
                old = d.group(2)
                lines[j] = f"{d.group(1)}digest: {digest}\n"
                return "".join(lines), old
        raise PromoteError(
            f"la imagen {image} no tiene línea digest en la kustomization"
        )
    raise PromoteError(
        f"la imagen {image} no está en el bloque images de la kustomization"
    )


def main(argv: list[str]) -> int:
    if argv[:1] == ["images"]:
        for ref, pinned in images(sys.stdin.read()):
            print(f"{ref}\t{'fijada' if pinned else 'sin-fijar'}")
        return 0
    if argv[:1] == ["set"] and len(argv) == 4:
        path, image, digest = Path(argv[1]), argv[2], argv[3]
        try:
            new, old = set_digest(path.read_text(encoding="utf-8"), image, digest)
        except PromoteError as exc:
            print(f"::error file={path}::{exc}", file=sys.stderr)
            return 1
        print(old)
        if old == digest:
            return 3
        path.write_text(new, encoding="utf-8")
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
