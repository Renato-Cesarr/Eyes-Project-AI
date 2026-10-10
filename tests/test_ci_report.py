import subprocess
from pathlib import Path

import pytest

from eyes_project_ai.ci_report import source_commit


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    def git(*args: str) -> None:
        subprocess.run(["git", "-C", str(tmp_path), *args], check=True, capture_output=True)

    git("init")
    git("config", "user.name", "Fixture")
    git("config", "user.email", "fixture@example.invalid")
    (tmp_path / "source.txt").write_text("original", encoding="utf-8")
    git("add", "source.txt")
    git("commit", "-m", "fixture")
    return tmp_path


def test_source_commit_refuses_modified_input(repository: Path) -> None:
    assert len(source_commit(repository)) == 40
    (repository / "source.txt").write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError, match="clean checkout"):
        source_commit(repository)


def test_source_commit_refuses_untracked_input(repository: Path) -> None:
    (repository / "untracked.py").write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError, match="clean checkout"):
        source_commit(repository)
