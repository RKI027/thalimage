"""Sidecars: non-media files named after a media file in the same folder
("img.png" -> "img.txt" or "img.png.txt"). They go with their media file
when it is deleted, unless another media file there claims them too."""

import hashlib
import json
import os
import shutil
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from thalimage.core.sidecars import sidecars_of
from tests.helpers import scan_source

COPY = str(Path("sub") / "a-copy.png")


def test_sidecars_are_the_files_named_after_the_media_file(tmp_path: Path) -> None:
    media = tmp_path / "img.png"
    media.touch()
    for name in ("img.txt", "img.png.json", "img.jpg", "other.txt", "img2.txt", ".DS_Store"):
        (tmp_path / name).touch()
    (tmp_path / "img.d").mkdir()

    assert [p.name for p in sidecars_of(media)] == ["img.png.json", "img.txt"]


def test_a_media_file_alone_has_no_sidecars(tmp_path: Path) -> None:
    (tmp_path / "img.png").touch()
    assert sidecars_of(tmp_path / "img.png") == []


@pytest.fixture
def duplicated(client: TestClient, image_dir: Path) -> tuple[int, str]:
    """a.png and its copy sub/a-copy.png, each with a .txt sidecar; the
    copy's says something the original's does not."""
    shutil.copy(image_dir / "a.png", image_dir / COPY)
    (image_dir / "a.txt").write_text("steps: 20")
    (image_dir / "sub" / "a-copy.txt").write_text("steps: 30")
    source_id, _ = scan_source(client, image_dir)
    client.patch(f"/api/v1/sources/{source_id}", json={"writable": True})
    [group] = client.get(f"/api/v1/sources/{source_id}/summary").json()["duplicates"]
    return source_id, group["content_hash"]


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def test_the_summary_lists_each_copy_s_sidecars_with_a_digest(
    client: TestClient, duplicated: tuple[int, str]
) -> None:
    source_id, _ = duplicated

    [group] = client.get(f"/api/v1/sources/{source_id}/summary").json()["duplicates"]

    assert group["sidecars"] == {
        "a.png": [{"relative_path": "a.txt", "digest": _digest("steps: 20")}],
        COPY: [
            {"relative_path": str(Path("sub") / "a-copy.txt"), "digest": _digest("steps: 30")}
        ],
    }


def test_deleting_a_copy_deletes_its_sidecars(
    client: TestClient, db: sqlite3.Connection, image_dir: Path, duplicated: tuple[int, str]
) -> None:
    source_id, _ = duplicated
    sidecar = str(Path("sub") / "a-copy.txt")

    resp = client.post(f"/api/v1/sources/{source_id}/delete-copies", json={"paths": [COPY]})

    assert resp.json() == {"deleted": [COPY], "sidecars": [sidecar], "failed": []}
    assert not (image_dir / sidecar).exists()
    assert (image_dir / "a.txt").exists()
    rows = db.execute("SELECT path, outcome FROM file_changes ORDER BY id").fetchall()
    assert [tuple(r) for r in rows] == [(COPY, "done"), (sidecar, "done")]


def test_a_sidecar_another_media_file_claims_is_kept(
    client: TestClient, image_dir: Path, duplicated: tuple[int, str]
) -> None:
    source_id, _ = duplicated
    Image.new("RGB", (8, 8), "yellow").save(image_dir / "sub" / "a-copy.jpg")
    client.post(f"/api/v1/sources/{source_id}/scan")
    client.get(f"/api/v1/sources/{source_id}/scan/status")

    resp = client.post(f"/api/v1/sources/{source_id}/delete-copies", json={"paths": [COPY]})

    assert resp.json()["sidecars"] == []
    assert (image_dir / "sub" / "a-copy.txt").exists()


def test_a_sidecar_that_cannot_be_removed_is_reported(
    client: TestClient,
    image_dir: Path,
    duplicated: tuple[int, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_id, _ = duplicated
    real_remove = os.remove

    def refuse_sidecars(path: object) -> None:
        if str(path).endswith(".txt"):
            raise PermissionError(13, "Permission denied", str(path))
        real_remove(path)  # type: ignore[arg-type]

    monkeypatch.setattr(os, "remove", refuse_sidecars)
    resp = client.post(f"/api/v1/sources/{source_id}/delete-copies", json={"paths": [COPY]})

    body = resp.json()
    assert body["deleted"] == [COPY] and body["sidecars"] == []
    [failure] = body["failed"]
    assert failure["relative_path"] == str(Path("sub") / "a-copy.txt")


def test_deleting_an_image_deletes_every_copy_s_sidecars(
    client: TestClient, image_dir: Path, duplicated: tuple[int, str]
) -> None:
    _, content_hash = duplicated

    copies = client.get(f"/api/v1/images/{content_hash}/copies").json()
    assert [c["sidecars"] for c in copies] == [["a.txt"], [str(Path("sub") / "a-copy.txt")]]

    resp = client.post(f"/api/v1/images/{content_hash}/delete")

    assert resp.json() == {"deleted": 2, "sidecars": 2, "failed": []}
    assert not (image_dir / "a.txt").exists()
    assert not (image_dir / "sub" / "a-copy.txt").exists()


def _contents(client: TestClient, content_hash: str) -> list[dict]:
    resp = client.get(f"/api/v1/images/{content_hash}/sidecars")
    assert resp.status_code == 200
    return resp.json()


def test_the_sidecars_of_every_copy_are_read(
    client: TestClient, duplicated: tuple[int, str]
) -> None:
    source_id, content_hash = duplicated

    assert _contents(client, content_hash) == [
        {"source_id": source_id, "relative_path": "a.txt", "size": 9, "text": "steps: 20"},
        {"source_id": source_id, "relative_path": str(Path("sub") / "a-copy.txt"),
         "size": 9, "text": "steps: 30"},
    ]


def test_binary_or_large_sidecars_are_listed_without_their_text(
    client: TestClient, image_dir: Path
) -> None:
    (image_dir / "a.bin").write_bytes(b"\xff\xfe\x00")
    (image_dir / "a.png.json").write_text("x" * (256 * 1024 + 1))
    source_id, hashes = scan_source(client, image_dir)

    assert _contents(client, hashes[0]) == [
        {"source_id": source_id, "relative_path": "a.bin", "size": 3, "text": None},
        {"source_id": source_id, "relative_path": "a.png.json", "size": 256 * 1024 + 1, "text": None},
    ]


def test_the_sidecars_of_an_unknown_image_are_a_404(client: TestClient) -> None:
    assert client.get(f"/api/v1/images/{'0' * 64}/sidecars").status_code == 404


def _orphans(client: TestClient, source_id: int) -> list[str]:
    return client.get(f"/api/v1/sources/{source_id}/summary").json()["orphans"]


def _rescan(client: TestClient, source_id: int) -> dict:
    """Scan again to the end; return the last status event."""
    client.post(f"/api/v1/sources/{source_id}/scan")
    resp = client.get(f"/api/v1/sources/{source_id}/scan/status")
    return [
        json.loads(line[len("data: "):])
        for line in resp.text.splitlines()
        if line.startswith("data: ")
    ][-1]


def test_files_no_media_file_names_are_orphans(client: TestClient, image_dir: Path) -> None:
    (image_dir / "a.txt").write_text("steps: 20")
    (image_dir / "sub" / "c.png.json").write_text("{}")
    (image_dir / "sub" / "notes.md").write_text("todo")
    source_id, _ = scan_source(client, image_dir)

    assert _orphans(client, source_id) == ["readme.txt", str(Path("sub") / "notes.md")]


def test_a_sidecar_whose_media_file_is_gone_is_an_orphan(
    client: TestClient, image_dir: Path
) -> None:
    (image_dir / "a.txt").write_text("steps: 20")
    source_id, _ = scan_source(client, image_dir)
    (image_dir / "a.png").unlink()

    _rescan(client, source_id)

    assert "a.txt" in _orphans(client, source_id)


def test_the_scan_status_counts_the_sidecars(client: TestClient, image_dir: Path) -> None:
    source_id, _ = scan_source(client, image_dir)
    (image_dir / "a.txt").write_text("steps: 20")

    status = _rescan(client, source_id)

    assert (status["sidecars_added"], status["sidecars_changed"], status["sidecars_removed"]) == (
        1, 0, 0
    )


def test_a_sidecar_deleted_with_its_copy_is_not_reported_removed(
    client: TestClient, duplicated: tuple[int, str]
) -> None:
    source_id, _ = duplicated
    client.post(f"/api/v1/sources/{source_id}/delete-copies", json={"paths": [COPY]})

    assert _rescan(client, source_id)["sidecars_removed"] == 0
