"""A source set to rename its files to their picture hash (#14) does so at
the end of every scan, only in that source; a file it cannot rename is
listed among the scan's failures."""

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.helpers import scan_source
from thalimage.core.picture_hash import picture_hash


def _set(client: TestClient, source_id: int, **changes: bool):  # type: ignore[no-untyped-def]
    return client.patch(f"/api/v1/sources/{source_id}", json=changes)


def _rescan(client: TestClient, source_id: int) -> str:
    """Scan again; the scan's last status event."""
    client.post(f"/api/v1/sources/{source_id}/scan")
    return client.get(f"/api/v1/sources/{source_id}/scan/status").text


def _files(folder: Path) -> set[str]:
    return {str(p.relative_to(folder)) for p in folder.rglob("*") if p.is_file()}


@pytest.fixture
def hashes(image_dir: Path) -> dict[str, str]:
    return {name: picture_hash(image_dir / name) for name in ("a.png", "b.jpg", "sub/c.png")}


def test_a_read_only_source_cannot_be_set_to_rename(
    client: TestClient, image_dir: Path
) -> None:
    source_id, _ = scan_source(client, image_dir)

    resp = _set(client, source_id, rename_to_hash=True)

    assert resp.status_code == 409
    assert client.get("/api/v1/sources").json()[0]["rename_to_hash"] is False


def test_a_writable_source_can_be_set_to_rename(client: TestClient, image_dir: Path) -> None:
    source_id, _ = scan_source(client, image_dir)

    resp = _set(client, source_id, writable=True, rename_to_hash=True)

    assert resp.status_code == 200
    assert resp.json()["rename_to_hash"] is True


def test_making_a_source_read_only_stops_renaming(client: TestClient, image_dir: Path) -> None:
    source_id, _ = scan_source(client, image_dir)
    _set(client, source_id, writable=True, rename_to_hash=True)

    resp = _set(client, source_id, writable=False)

    assert resp.json()["rename_to_hash"] is False


def test_a_scan_renames_every_file_of_the_source(
    client: TestClient, image_dir: Path, hashes: dict[str, str]
) -> None:
    shutil.copy(image_dir / "a.png", image_dir / "a (1).png")
    source_id, _ = scan_source(client, image_dir)
    _set(client, source_id, writable=True, rename_to_hash=True)

    status = _rescan(client, source_id)

    assert '"renamed":3' in status
    assert _files(image_dir) == {
        f"{hashes['a.png']}.png",
        f"{hashes['b.jpg']}.jpg",
        str(Path("sub") / f"{hashes['sub/c.png']}.png"),
        "readme.txt",
    }


def test_only_the_sources_set_to_rename_are_renamed(
    client: TestClient, image_dir: Path, tmp_path: Path, hashes: dict[str, str]
) -> None:
    other = tmp_path / "other"
    other.mkdir()
    shutil.copy(image_dir / "a.png", other / "a.png")
    source_id, _ = scan_source(client, image_dir)
    other_id, _ = scan_source(client, other)
    _set(client, other_id, writable=True)
    _set(client, source_id, writable=True, rename_to_hash=True)

    _rescan(client, source_id)

    assert _files(other) == {"a.png"}
    assert f"{hashes['a.png']}.png" in _files(image_dir)


def test_a_file_that_cannot_be_renamed_is_listed_and_the_rest_renamed(
    client: TestClient, image_dir: Path, hashes: dict[str, str]
) -> None:
    source_id, _ = scan_source(client, image_dir)
    _set(client, source_id, writable=True, rename_to_hash=True)
    (image_dir / f"{hashes['a.png']}.png").write_bytes(b"not this image")

    _rescan(client, source_id)

    assert (image_dir / "a.png").exists()
    assert f"{hashes['b.jpg']}.jpg" in _files(image_dir)
    failures = client.get(f"/api/v1/sources/{source_id}/summary").json()["failures"]
    assert any(
        f["relative_path"] == "a.png" and "Not renamed" in f["reason"] for f in failures
    )


def test_a_folder_refusing_writes_is_listed_and_the_scan_completes(
    client: TestClient, image_dir: Path
) -> None:
    source_id, _ = scan_source(client, image_dir)
    _set(client, source_id, writable=True, rename_to_hash=True)
    image_dir.chmod(0o555)
    try:
        status = _rescan(client, source_id)
    finally:
        image_dir.chmod(0o755)

    assert '"phase":"complete"' in status
    assert (image_dir / "a.png").exists()
    failures = client.get(f"/api/v1/sources/{source_id}/summary").json()["failures"]
    assert [f["relative_path"] for f in failures if "Not renamed" in f["reason"]] == ["./"]
