"""Folder tags: the `folder:` tags derived from where an image's files are."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from tests.helpers import scan_source


def _write(root: Path, relative: str, colour: tuple[int, int, int]) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (8, 8), colour).save(path)


@pytest.fixture
def library(tmp_path: Path) -> Path:
    """A source with files at the top, in nested folders, and in a folder
    whose name starts like another's."""
    root = tmp_path / "library"
    _write(root, "top.png", (10, 0, 0))
    _write(root, "portraits/a.png", (20, 0, 0))
    _write(root, "portraits/2024/b.png", (30, 0, 0))
    _write(root, "portraitsX/c.png", (40, 0, 0))
    _write(root, "landscapes/d.png", (50, 0, 0))
    return root


def _filenames(client: TestClient, tag: str) -> set[str]:
    items = client.get("/api/v1/images", params={"tags": tag}).json()["items"]
    return {i["filename"] for i in items}


def test_folder_filter_matches_the_folder_and_its_subfolders(
    client: TestClient, library: Path
) -> None:
    scan_source(client, library)
    assert _filenames(client, "folder:portraits") == {"a.png", "b.png"}


def test_folder_filter_ignores_surrounding_slashes(client: TestClient, library: Path) -> None:
    scan_source(client, library)
    assert _filenames(client, "folder:/portraits/2024/") == {"b.png"}


def _detail(client: TestClient, filename: str) -> dict[str, object]:
    items = client.get("/api/v1/images").json()["items"]
    content_hash = next(i["content_hash"] for i in items if i["filename"] == filename)
    return dict(client.get(f"/api/v1/images/{content_hash}").json())


def test_image_detail_lists_its_folder_tags(client: TestClient, library: Path) -> None:
    scan_source(client, library)
    assert _detail(client, "b.png")["folder_tags"] == ["folder:portraits/2024"]
    assert _detail(client, "top.png")["folder_tags"] == []


def test_copies_in_several_folders_give_one_tag_each(client: TestClient, library: Path) -> None:
    _write(library, "landscapes/a.png", (20, 0, 0))
    _write(library, "portraits/again/a.png", (20, 0, 0))
    scan_source(client, library)
    assert _detail(client, "a.png")["folder_tags"] == [
        "folder:landscapes",
        "folder:portraits",
        "folder:portraits/again",
    ]
    assert "a.png" in _filenames(client, "folder:landscapes")


@pytest.mark.parametrize("name", ["folder:mine", "Folder:mine"])
def test_a_tag_cannot_be_named_like_a_folder_tag(client: TestClient, name: str) -> None:
    assert client.post("/api/v1/tags", json={"name": name}).status_code == 422
    tag_id = client.post("/api/v1/tags", json={"name": "mine"}).json()["id"]
    assert client.patch(f"/api/v1/tags/{tag_id}", json={"name": name}).status_code == 422
