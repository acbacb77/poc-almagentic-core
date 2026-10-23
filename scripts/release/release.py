#!/usr/bin/env python3
"""Calcula la siguiente versión y las notas a partir del historial de main (tarea B).

Uso:
  release.py --repo-dir . --range vX.Y.Z..HEAD --last-tag vX.Y.Z --initial 1.0.0 --repo owner/repo [--date AAAA-MM-DD]
  (o con el historial por la entrada estándar: registros «sha␟autor␟asunto␟cuerpo␞»)

Imprime JSON: {"bump": "major|minor|patch|none", "version": "X.Y.Z", "notes": "markdown"}.

Entiende los dos estilos de merge de la POC: *merge commit* («Merge pull request #N …» con el
título del PR en el cuerpo) y *squash* («título (#N)»). Los títulos siguen Conventional Commits:
  feat → minor; fix, perf, refactor, build, ci, deps, revert → patch;
  «!» o BREAKING CHANGE → major; docs, test, chore, style, spec → sin versión.
Marca con 🤖 los cambios en los que hay commits del agente (autor o coautor). Los mensajes que no
siguen Conventional Commits no se listan; solo se cuentan.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass

CC = re.compile(
    r"^(?P<type>[a-z]+)(?:\((?P<scope>[^)]*)\))?(?P<bang>!)?:\s*(?P<desc>.+)$"
)
MERGE = re.compile(r"^Merge pull request #(?P<pr>\d+) from \S+")
SQUASH_PR = re.compile(r"\s*\(#(?P<pr>\d+)\)\s*$")
VERSION = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")
AGENT = "almagentic-agent[bot]"

PATCH_TYPES = {"fix", "perf", "refactor", "build", "ci", "deps", "revert"}
SECTIONS = [
    ("breaking", "⚠️ Cambios incompatibles"),
    ("feat", "Novedades"),
    ("fix", "Correcciones"),
    ("other", "Otros cambios"),
]
ORDER = {"none": 0, "patch": 1, "minor": 2, "major": 3}


@dataclass
class Change:
    type: str
    scope: str
    desc: str
    pr: str
    breaking: bool
    agent: bool

    @property
    def bump(self) -> str:
        if self.breaking:
            return "major"
        if self.type == "feat":
            return "minor"
        return "patch" if self.type in PATCH_TYPES else "none"


def parse(log: str) -> list[Change]:
    changes = []
    for record in log.split("\x1e"):
        record = record.strip("\n")
        if not record.strip():
            continue
        _sha, author, subject, body = (record.split("\x1f") + ["", "", ""])[:4]
        agent = AGENT in author or AGENT in body
        pr = ""
        m = MERGE.match(subject)
        if m:
            pr = m.group("pr")
            title = next(
                (line.strip() for line in body.splitlines() if line.strip()), ""
            )
        else:
            title = subject.strip()
            # El último «(#N)» es el PR del squash; uno anterior puede ser el issue.
            m2 = SQUASH_PR.search(title)
            if m2:
                pr = m2.group("pr")
                title = title[: m2.start()].rstrip()
        cc = CC.match(title)
        if not cc:
            changes.append(Change("", "", title, pr, False, agent))
            continue
        breaking = bool(cc.group("bang")) or "BREAKING CHANGE" in body
        # Sin el prefijo de la plantilla de peticiones ("[Petición] ").
        desc = re.sub(r"^\[[^\]]{1,30}\]\s*", "", cc.group("desc").strip())
        changes.append(
            Change(
                cc.group("type"),
                cc.group("scope") or "",
                desc,
                pr,
                breaking,
                agent,
            )
        )
    return changes


def next_version(last: str, bump: str, initial: str) -> str:
    if not last:
        return initial.lstrip("v")
    m = VERSION.match(last)
    if not m:
        raise ValueError(f"etiqueta no válida: {last}")
    major, minor, patch = map(int, m.groups())
    if bump == "major":
        return f"{major + 1}.0.0"
    if bump == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def section_of(change: Change) -> str | None:
    if change.breaking:
        return "breaking"
    if change.type in ("feat", "fix"):
        return change.type
    if change.bump == "patch":
        return "other"
    return None


def notes(changes: list[Change], version: str, repo: str, date: str, last: str) -> str:
    out = [f"## v{version}" + (f" ({date})" if date else ""), ""]
    for key, title in SECTIONS:
        items = [c for c in changes if section_of(c) == key]
        if not items:
            continue
        out += [f"### {title}", ""]
        for c in items:
            scope = f"**{c.scope}:** " if c.scope else ""
            link = (
                f" ([#{c.pr}](https://github.com/{repo}/pull/{c.pr}))"
                if c.pr and repo
                else ""
            )
            out.append(f"- {scope}{c.desc}{link}{' 🤖' if c.agent else ''}")
        out.append("")
    quiet = [c for c in changes if section_of(c) is None]
    if quiet:
        out += [
            f"Además, {len(quiet)} cambio(s) de documentación, especificación o pruebas.",
            "",
        ]
    if any(c.agent for c in changes):
        out += [
            "🤖 = cambio con commits del agente (`almagentic-agent[bot]`), revisado y aprobado por una persona.",
            "",
        ]
    if last and repo:
        out += [
            f"Todos los cambios: https://github.com/{repo}/compare/{last}...v{version}",
            "",
        ]
    return "\n".join(out).rstrip() + "\n"


def plan(log: str, last: str, initial: str, repo: str, date: str = "") -> dict:
    changes = parse(log)
    bump = max((c.bump for c in changes), key=ORDER.__getitem__, default="none")
    if bump == "none":
        return {"bump": "none", "version": last.lstrip("v"), "notes": ""}
    version = next_version(last, bump, initial)
    return {
        "bump": bump,
        "version": version,
        "notes": notes(changes, version, repo, date, last),
    }


def git_log(repo_dir: str, rev_range: str) -> str:
    """Historial de primer padre. En los merge commits, el autor incluye a los de los commits fusionados."""

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", "-C", repo_dir, *args], check=True, capture_output=True, text=True
        ).stdout

    out = []
    raw = git(
        "log", "--first-parent", "--format=%H%x1f%P%x1f%an%x1f%s%x1f%b%x1e", rev_range
    )
    for record in raw.split("\x1e"):
        record = record.strip("\n")
        if not record.strip():
            continue
        sha, parents, author, subject, body = (record.split("\x1f") + [""] * 4)[:5]
        parents = parents.split()
        if len(parents) > 1:
            merged = git("log", "--format=%an", f"{parents[0]}..{parents[1]}").split()
            author = ";".join([author, *merged])
        out.append("\x1f".join([sha, author, subject, body]) + "\x1e")
    return "".join(out)


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--repo-dir",
        default="",
        help="lee el historial con git en lugar de la entrada estándar",
    )
    p.add_argument("--range", default="HEAD")
    p.add_argument("--last-tag", default="")
    p.add_argument("--initial", default="1.0.0")
    p.add_argument("--repo", default="")
    p.add_argument("--date", default="")
    a = p.parse_args(argv)
    log = git_log(a.repo_dir, a.range) if a.repo_dir else sys.stdin.read()
    json.dump(
        plan(log, a.last_tag, a.initial, a.repo, a.date),
        sys.stdout,
        ensure_ascii=False,
    )
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
