import base64
import os
import subprocess

import pytest

from api_commit import UnsupportedChange, collect_changes, mutation_input


def run(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    run(tmp_path, "init", "-q")
    run(tmp_path, "config", "user.email", "t@e")
    run(tmp_path, "config", "user.name", "t")
    (tmp_path / "keep.txt").write_text("a\n")
    (tmp_path / "gone.txt").write_text("b\n")
    (tmp_path / "dir with space").mkdir()
    (tmp_path / "dir with space" / "x.py").write_text("x = 1\n")
    run(tmp_path, "add", "-A")
    run(tmp_path, "commit", "-qm", "base")
    return tmp_path


def commit(repo, msg="cambio"):
    run(repo, "add", "-A")
    run(repo, "commit", "-qm", msg)


def test_recoge_altas_cambios_y_bajas(repo):
    (repo / "keep.txt").write_text("a2\n")
    (repo / "gone.txt").unlink()
    (repo / "nuevo.bin").write_bytes(b"\x00\xff")
    (repo / "dir with space" / "x.py").write_text("x = 2\n")
    commit(repo)
    additions, deletions = collect_changes(str(repo))
    by_path = {a["path"]: base64.b64decode(a["contents"]) for a in additions}
    assert by_path == {
        "keep.txt": b"a2\n",
        "nuevo.bin": b"\x00\xff",
        "dir with space/x.py": b"x = 2\n",
    }
    assert deletions == [{"path": "gone.txt"}]


def test_rechaza_ejecutables(repo):
    f = repo / "script.sh"
    f.write_text("#!/bin/sh\n")
    os.chmod(f, 0o755)
    commit(repo)
    with pytest.raises(UnsupportedChange, match="ejecutable"):
        collect_changes(str(repo))


def test_rechaza_enlaces_simbolicos(repo):
    (repo / "enlace").symlink_to("keep.txt")
    commit(repo)
    with pytest.raises(UnsupportedChange, match="enlace"):
        collect_changes(str(repo))


def test_entrada_de_la_mutacion():
    payload = mutation_input(
        "o/r",
        "feat/1-x",
        "abc",
        "feat: x",
        "Refs #1",
        [{"path": "a", "contents": "YQ=="}],
        [],
    )
    inp = payload["variables"]["input"]
    assert "createCommitOnBranch" in payload["query"]
    assert inp["branch"] == {"repositoryNameWithOwner": "o/r", "branchName": "feat/1-x"}
    assert inp["expectedHeadOid"] == "abc"
    assert inp["message"] == {"headline": "feat: x", "body": "Refs #1"}
    assert inp["fileChanges"]["deletions"] == []


def test_mensaje_sin_cuerpo():
    payload = mutation_input("o/r", "b", "abc", "fix: y", "", [], [{"path": "z"}])
    assert payload["variables"]["input"]["message"] == {"headline": "fix: y"}
