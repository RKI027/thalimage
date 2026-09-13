"""Tests for build version reporting."""

import subprocess
from pathlib import Path

from thalimage.version import describe_commit, version_info


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=T", *args],
        cwd=repo, check=True, capture_output=True,
    )


def _repo_with_commit(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "a.txt").write_text("hello")
    _git(repo, "add", "a.txt")
    _git(repo, "commit", "-q", "-m", "first")
    return repo


def test_describe_commit_is_none_outside_a_repo(tmp_path: Path) -> None:
    assert describe_commit(tmp_path) is None


def test_describe_commit_is_none_for_a_missing_directory(tmp_path: Path) -> None:
    assert describe_commit(tmp_path / "nope") is None


def test_describe_commit_returns_the_short_sha_when_untagged(tmp_path: Path) -> None:
    repo = _repo_with_commit(tmp_path)
    described = describe_commit(repo)
    assert described is not None
    assert described.isalnum()


def test_describe_commit_prefers_a_tag(tmp_path: Path) -> None:
    repo = _repo_with_commit(tmp_path)
    _git(repo, "tag", "v1.2.3")
    assert describe_commit(repo) == "v1.2.3"


def test_describe_commit_counts_commits_since_the_tag(tmp_path: Path) -> None:
    repo = _repo_with_commit(tmp_path)
    _git(repo, "tag", "v1.2.3")
    (repo / "b.txt").write_text("more")
    _git(repo, "add", "b.txt")
    _git(repo, "commit", "-q", "-m", "second")

    described = describe_commit(repo)
    assert described is not None
    assert described.startswith("v1.2.3-1-g")


def test_describe_commit_marks_a_dirty_tree(tmp_path: Path) -> None:
    repo = _repo_with_commit(tmp_path)
    (repo / "a.txt").write_text("changed")
    described = describe_commit(repo)
    assert described is not None
    assert described.endswith("-dirty")


def test_version_info_reports_the_package_version() -> None:
    info = version_info()
    assert info.version
    assert info.version[0].isdigit()
