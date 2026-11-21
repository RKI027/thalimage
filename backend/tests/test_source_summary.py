"""A source's summary explains its file count against its image count:
copies of the same content, files the last scan could not index, and
archived images."""

import os
import shutil
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image, PngImagePlugin

from tests.helpers import ensure_source, insert_image, scan_source
from thalimage.services.source_summary import Sidecar, source_summary


def _summary(client: TestClient, source_id: int) -> dict:
    resp = client.get(f"/api/v1/sources/{source_id}/summary")
    assert resp.status_code == 200
    return resp.json()


def _rescan(client: TestClient, source_id: int) -> None:
    client.post(f"/api/v1/sources/{source_id}/scan")
    client.get(f"/api/v1/sources/{source_id}/scan/status")


def test_a_clean_source_has_as_many_images_as_files(client: TestClient, image_dir: Path) -> None:
    source_id, hashes = scan_source(client, image_dir)

    summary = _summary(client, source_id)

    assert (summary["files"], summary["images"]) == (len(hashes), len(hashes))
    assert (summary["duplicates"], summary["failures"], summary["archived"]) == ([], [], [])


def test_copies_of_one_content_are_grouped(client: TestClient, image_dir: Path) -> None:
    shutil.copy(image_dir / "a.png", image_dir / "sub" / "a-copy.png")
    source_id, hashes = scan_source(client, image_dir)

    summary = _summary(client, source_id)

    assert (summary["files"], summary["images"]) == (4, 3)
    [group] = summary["duplicates"]
    assert group["paths"] == ["a.png", str(Path("sub") / "a-copy.png")]
    assert group["content_hash"] in hashes


def test_each_copy_has_its_file_version(client: TestClient, image_dir: Path) -> None:
    """Copies of one picture with different metadata are different file
    versions; identical copies share theirs."""
    for name, prompt in [("p.png", "a lighthouse"), ("p-copy.png", "a lighthouse"), ("p-edit.png", "a harbour")]:
        info = PngImagePlugin.PngInfo()
        info.add_text("parameters", prompt)
        Image.new("RGB", (8, 8), "teal").save(image_dir / name, pnginfo=info)
    source_id, _ = scan_source(client, image_dir)

    [group] = _summary(client, source_id)["duplicates"]

    versions = group["file_hashes"]
    assert group["paths"] == ["p-copy.png", "p-edit.png", "p.png"]
    assert versions["p.png"] == versions["p-copy.png"]
    assert versions["p-edit.png"] != versions["p.png"]


def test_a_summary_with_many_copies_reads_no_folders(
    db, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The summary used to list the folder once per duplicate path, then
    read every sidecar in it again: O(paths x folder size)."""
    source_id = ensure_source(db, str(tmp_path / "source"))
    content_hash = "a" * 64
    insert_image(db, content_hash, source_id=source_id, filename="img0000.png")
    db.execute("DELETE FROM image_locations WHERE source_id = ?", (source_id,))
    db.executemany(
        "INSERT INTO image_locations"
        " (source_id, relative_path, content_hash, filename, file_size, file_modified)"
        " VALUES (?, ?, ?, ?, 1, '2024-01-01T00:00:00')",
        [(source_id, f"img{i:04}.png", content_hash, f"img{i:04}.png") for i in range(1000)],
    )
    db.executemany(
        "INSERT INTO sidecars"
        " (source_id, relative_path, digest, file_size, file_modified, orphan)"
        " VALUES (?, ?, 'd', 1, '2024-01-01T00:00:00', ?)",
        [
            (source_id, f"img{i:04}.txt" if i < 1000 else f"other{i:04}.txt", int(i >= 1000))
            for i in range(5000)
        ],
    )
    db.commit()

    def no_listing(self: Path) -> None:
        raise AssertionError(f"listed {self}")

    monkeypatch.setattr(Path, "iterdir", no_listing)
    started = time.perf_counter()
    summary = source_summary(db, source_id)
    elapsed = time.perf_counter() - started

    assert summary is not None
    [group] = summary.duplicates
    assert len(group.paths) == 1000
    assert group.sidecars["img0000.png"] == [
        Sidecar(relative_path="img0000.txt", digest="d")
    ]
    assert summary.orphans == [f"other{i:04}.txt" for i in range(1000, 5000)]
    assert elapsed < 1.0


def test_a_file_that_fails_is_listed_with_its_reason(client: TestClient, image_dir: Path) -> None:
    (image_dir / "broken.png").write_bytes(b"\x89PNG not really")
    source_id, _ = scan_source(client, image_dir)

    [failure] = _summary(client, source_id)["failures"]

    assert failure["relative_path"] == "broken.png"
    assert failure["reason"]
    assert str(image_dir) not in failure["reason"]


def test_a_rescan_replaces_the_failures(client: TestClient, image_dir: Path) -> None:
    broken = image_dir / "broken.png"
    broken.write_bytes(b"\x89PNG not really")
    source_id, _ = scan_source(client, image_dir)
    Image.new("RGB", (10, 10), "white").save(broken)

    _rescan(client, source_id)

    assert _summary(client, source_id)["failures"] == []


def test_an_unreadable_folder_is_listed(
    client: TestClient, image_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_scandir = os.scandir

    def scandir(path: object = ".") -> object:
        if Path(str(path)) == image_dir / "sub":
            raise PermissionError(13, "Permission denied", str(path))
        return real_scandir(path)  # type: ignore[arg-type]

    monkeypatch.setattr(os, "scandir", scandir)
    source_id, _ = scan_source(client, image_dir)

    [failure] = _summary(client, source_id)["failures"]

    assert failure["relative_path"] == "sub" + os.sep
    assert "could not be read" in failure["reason"]


def test_archived_images_are_listed_apart(client: TestClient, image_dir: Path) -> None:
    source_id, hashes = scan_source(client, image_dir)
    client.patch(f"/api/v1/images/{hashes[0]}/archive", json={"archived": True})

    summary = _summary(client, source_id)

    assert (summary["files"], summary["images"]) == (3, 2)
    [archived] = summary["archived"]
    assert archived["content_hash"] == hashes[0]
    assert archived["relative_path"] == "a.png"


def test_deleting_a_source_drops_its_failures(client: TestClient, image_dir: Path) -> None:
    (image_dir / "broken.png").write_bytes(b"\x89PNG not really")
    source_id, _ = scan_source(client, image_dir)

    assert client.delete(f"/api/v1/sources/{source_id}").status_code == 204
    assert client.get(f"/api/v1/sources/{source_id}/summary").status_code == 404


def test_images_found_nowhere_else_are_counted(
    client: TestClient, image_dir: Path, tmp_path: Path
) -> None:
    """What removing the source would take with it: archived images
    included, images also in another source not."""
    other = tmp_path / "other"
    other.mkdir()
    shutil.copy(image_dir / "a.png", other / "a.png")
    source_id, hashes = scan_source(client, image_dir)
    scan_source(client, other)
    # Listed by name: a.png, b.jpg, sub/c.png.
    client.patch(f"/api/v1/images/{hashes[1]}/archive", json={"archived": True})

    assert _summary(client, source_id)["only_here"] == 2
