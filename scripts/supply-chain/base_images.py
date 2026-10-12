#!/usr/bin/env python3
"""Lista las imágenes base de un Dockerfile y comprueba que van fijadas por digest (tarea 9).

Uso: base_images.py <Dockerfile>
Imprime una imagen por línea con el formato `<imagen>\t<fijada|sin-fijar>`. Las
referencias a etapas anteriores (`FROM build`) y `scratch` no son imágenes base.
No admite `ARG` en `FROM`: la imagen tiene que leerse en el propio Dockerfile.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

FROM = re.compile(r"^\s*FROM\s+(?:--platform=\S+\s+)?(\S+)(?:\s+AS\s+(\S+))?\s*$", re.I)
DIGEST = re.compile(r"@sha256:[0-9a-f]{64}$")


class InvalidDockerfile(ValueError):
    pass


def base_images(text: str) -> list[tuple[str, bool]]:
    stages: set[str] = set()
    out: list[tuple[str, bool]] = []
    # Une las líneas partidas con barra invertida.
    for line in re.sub(r"\\\n", " ", text).splitlines():
        if not re.match(r"^\s*FROM\s", line, re.I):
            continue
        m = FROM.match(line)
        if not m:
            raise InvalidDockerfile(f"FROM no reconocido: {line.strip()}")
        image, alias = m.group(1), m.group(2)
        if "$" in image:
            raise InvalidDockerfile(f"FROM con variables no permitido: {image}")
        if image.lower() not in stages and image != "scratch":
            out.append((image, bool(DIGEST.search(image))))
        if alias:
            stages.add(alias.lower())
    if not out:
        raise InvalidDockerfile("el Dockerfile no tiene imágenes base")
    return out


def main(argv: list[str]) -> int:
    try:
        images = base_images(Path(argv[0]).read_text(encoding="utf-8"))
    except InvalidDockerfile as exc:
        print(f"::error file={argv[0]}::{exc}")
        return 1
    for image, pinned in images:
        print(f"{image}\t{'fijada' if pinned else 'sin-fijar'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
