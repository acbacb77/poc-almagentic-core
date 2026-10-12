#!/usr/bin/env python3
"""Publica un commit local a través de la API de GitHub para que salga firmado.

Uso: api_commit.py <repo-dir> <owner/repo> <rama> <commit-esperado> [--create-from SHA]

El job publish del agente ya ha aplicado el parche, ha hecho un commit local y lo ha
revisado con check_pr_files.py. Este script no hace `git push`: lee ese commit
(HEAD frente a HEAD~1) y lo recrea con la mutación GraphQL `createCommitOnBranch`.
GitHub firma los commits que una GitHub App crea por la API, así que el commit sale
como *Verified* y queda ligado a la App, no a un nombre de autor que cualquiera puede
escribir.

`expectedHeadOid` hace que la API rechace el commit si la rama ha cambiado desde
que el agente empezó. Con `--create-from` crea antes la rama apuntando a ese commit
(agente autónomo).

Limitaciones de la API, que se rechazan con un mensaje claro: ficheros ejecutables,
enlaces simbólicos y submódulos.

Imprime el SHA del commit creado.
"""

from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys

REGULAR = "100644"


class UnsupportedChange(ValueError):
    pass


def git(repo: str, *args: str, binary: bool = False) -> str | bytes:
    out = subprocess.run(["git", "-C", repo, *args], check=True, capture_output=True)
    return out.stdout if binary else out.stdout.decode()


def collect_changes(repo: str) -> tuple[list[dict], list[dict]]:
    """Ficheros añadidos o modificados (con su contenido en base64) y borrados de HEAD~1..HEAD."""
    additions: list[dict] = []
    deletions: list[dict] = []
    raw = str(git(repo, "diff", "--no-renames", "--raw", "-z", "HEAD~1", "HEAD"))
    parts = [p for p in raw.split("\0") if p]
    # Formato -z: ":<modo_ant> <modo_nuevo> <sha_ant> <sha_nuevo> <estado>\0<ruta>\0"
    for meta, path in zip(parts[0::2], parts[1::2], strict=True):
        _, new_mode, _, _, status = meta.lstrip(":").split()
        if status == "D":
            deletions.append({"path": path})
            continue
        if new_mode != REGULAR:
            kind = {
                "100755": "ejecutable",
                "120000": "enlace simbólico",
                "160000": "submódulo",
            }.get(new_mode, new_mode)
            raise UnsupportedChange(
                f"{path}: {kind}; la API de commits solo admite ficheros normales"
            )
        content = git(repo, "show", f"HEAD:{path}", binary=True)
        assert isinstance(content, bytes)
        additions.append({"path": path, "contents": base64.b64encode(content).decode()})
    return additions, deletions


def mutation_input(
    repo_full: str,
    branch: str,
    expected: str,
    headline: str,
    body: str,
    additions: list[dict],
    deletions: list[dict],
) -> dict:
    message = {"headline": headline}
    if body:
        message["body"] = body
    return {
        "query": (
            "mutation($input: CreateCommitOnBranchInput!) {"
            " createCommitOnBranch(input: $input) { commit { oid url } } }"
        ),
        "variables": {
            "input": {
                "branch": {"repositoryNameWithOwner": repo_full, "branchName": branch},
                "message": message,
                "expectedHeadOid": expected,
                "fileChanges": {"additions": additions, "deletions": deletions},
            }
        },
    }


def gh(*args: str, stdin: str | None = None) -> str:
    out = subprocess.run(
        ["gh", *args], input=stdin, check=True, capture_output=True, text=True
    )
    return out.stdout


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("repo_dir")
    p.add_argument("repo_full")
    p.add_argument("branch")
    p.add_argument("expected")
    p.add_argument("--create-from", default="")
    a = p.parse_args(argv)

    try:
        additions, deletions = collect_changes(a.repo_dir)
    except UnsupportedChange as exc:
        print(f"::error title=Cambio no admitido::{exc}", file=sys.stderr)
        return 2
    if not additions and not deletions:
        print("::error::El commit local no tiene cambios", file=sys.stderr)
        return 2
    headline, _, body = (
        str(git(a.repo_dir, "log", "-1", "--format=%B")).strip().partition("\n")
    )

    if a.create_from:
        gh(
            "api",
            f"repos/{a.repo_full}/git/refs",
            "-f",
            f"ref=refs/heads/{a.branch}",
            "-f",
            f"sha={a.create_from}",
        )

    payload = mutation_input(
        a.repo_full,
        a.branch,
        a.expected,
        headline.strip(),
        body.strip(),
        additions,
        deletions,
    )
    try:
        result = json.loads(
            gh("api", "graphql", "--input", "-", stdin=json.dumps(payload))
        )
        error = (
            (result.get("errors") or [{}])[0].get("message")
            if result.get("errors")
            else ""
        )
    except subprocess.CalledProcessError as exc:
        result, error = {}, (exc.stderr or exc.stdout or str(exc)).strip()
    if error:
        if a.create_from:
            # No dejar una rama vacía: bloquearía el siguiente intento del agente.
            subprocess.run(
                [
                    "gh",
                    "api",
                    "-X",
                    "DELETE",
                    f"repos/{a.repo_full}/git/refs/heads/{a.branch}",
                ],
                capture_output=True,
            )
        print(
            f"::error title=La API rechazó el commit::{' '.join(error.split())}",
            file=sys.stderr,
        )
        return 1
    oid = result["data"]["createCommitOnBranch"]["commit"]["oid"]
    check = json.loads(gh("api", f"repos/{a.repo_full}/commits/{oid}"))
    verification = check["commit"]["verification"]
    print(
        f"Commit {oid}: verified={verification['verified']} ({verification['reason']})",
        file=sys.stderr,
    )
    print(oid)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
