"""Renaming an image's files to its picture hash (#14): every copy, in
every source, keeps its folder and extension and takes the hash as its
name. A copy whose folder already holds the image under that name is
redundant and is deleted instead."""

import os
import shutil
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image, PngImagePlugin

from tests.helpers import scan_source
from thalimage.core.picture_hash import picture_hash


@pytest.fixture
def writable(client: TestClient, image_dir: Path) -> tuple[int, dict[str, str]]:
    """image_dir as a writable source, with its hashes by file name."""
    source_id, _ = scan_source(client, image_dir)
    client.patch(f"/api/v1/sources/{source_id}", json={"writable": True})
    items = client.get("/api/v1/images", params={"source_id": source_id}).json()["items"]
    return source_id, {i["filename"]: i["content_hash"] for i in items}


def _rename(client: TestClient, content_hash: str):  # type: ignore[no-untyped-def]
    return client.post(f"/api/v1/images/{content_hash}/rename")


def _files(folder: Path) -> set[str]:
    return {str(p.relative_to(folder)) for p in folder.rglob("*") if p.is_file()}


def test_renaming_gives_the_file_its_picture_hash_as_name(
    client: TestClient, image_dir: Path, writable: tuple[int, dict[str, str]]
) -> None:
    _, hashes = writable
    h = hashes["a.png"]

    resp = _rename(client, h)

    assert resp.status_code == 200
    assert resp.json() == {"renamed": 1, "deleted": 0, "kept_sidecars": [], "failed": []}
    assert not (image_dir / "a.png").exists()
    assert (image_dir / f"{h}.png").exists()
    detail = client.get(f"/api/v1/images/{h}").json()
    assert detail["filename"] == f"{h}.png"
    assert detail["relative_path"] == f"{h}.png"
    assert detail["original_name"] == "a.png"


def test_a_rename_is_recorded(
    client: TestClient,
    db: sqlite3.Connection,
    writable: tuple[int, dict[str, str]],
) -> None:
    source_id, hashes = writable
    h = hashes["a.png"]

    _rename(client, h)

    assert [tuple(r) for r in db.execute(
        "SELECT source_id, operation, path, target, outcome FROM file_changes"
    )] == [(source_id, "rename", "a.png", f"{h}.png", "done")]


def test_the_extension_is_kept_as_found(
    client: TestClient, image_dir: Path, tmp_path: Path
) -> None:
    folder = tmp_path / "upper"
    folder.mkdir()
    shutil.copy(image_dir / "a.png", folder / "A.PNG")
    source_id, [h] = scan_source(client, folder)
    client.patch(f"/api/v1/sources/{source_id}", json={"writable": True})

    _rename(client, h)

    assert _files(folder) == {f"{h}.PNG"}


def test_every_copy_is_renamed_in_its_own_folder(
    client: TestClient, image_dir: Path, tmp_path: Path
) -> None:
    shutil.copy(image_dir / "a.png", image_dir / "sub" / "a-copy.png")
    other = tmp_path / "other"
    other.mkdir()
    shutil.copy(image_dir / "a.png", other / "x.png")
    first, hashes = scan_source(client, image_dir)
    second, _ = scan_source(client, other)
    for source_id in (first, second):
        client.patch(f"/api/v1/sources/{source_id}", json={"writable": True})
    h = client.get("/api/v1/images", params={"source_id": second}).json()["items"][0]["content_hash"]

    resp = _rename(client, h)

    assert resp.json()["renamed"] == 3
    assert f"{h}.png" in _files(image_dir)
    assert str(Path("sub") / f"{h}.png") in _files(image_dir)
    assert _files(other) == {f"{h}.png"}
    copies = [c["relative_path"] for c in client.get(f"/api/v1/images/{h}/copies").json()]
    assert sorted(copies) == sorted([f"{h}.png", str(Path("sub") / f"{h}.png"), f"{h}.png"])


def test_a_file_already_named_after_its_hash_is_left_alone(
    client: TestClient, db: sqlite3.Connection, writable: tuple[int, dict[str, str]]
) -> None:
    _, hashes = writable
    h = hashes["a.png"]
    _rename(client, h)

    resp = _rename(client, h)

    assert resp.json() == {"renamed": 0, "deleted": 0, "kept_sidecars": [], "failed": []}
    assert db.execute("SELECT COUNT(*) FROM file_changes").fetchone()[0] == 1


def test_a_rescan_after_renaming_finds_nothing_new(
    client: TestClient, writable: tuple[int, dict[str, str]]
) -> None:
    source_id, hashes = writable
    _rename(client, hashes["a.png"])

    client.post(f"/api/v1/sources/{source_id}/scan")
    status = client.get(f"/api/v1/sources/{source_id}/scan/status").text

    assert '"added":0' in status
    detail = client.get(f"/api/v1/images/{hashes['a.png']}").json()
    assert detail["original_name"] == "a.png"


def test_renaming_an_unknown_image_is_a_404(client: TestClient) -> None:
    assert _rename(client, "0" * 64).status_code == 404


def _tagged(folder: Path, name: str) -> Path:
    """The red 10×10 picture of image_dir's a.png, with a comment in it."""
    info = PngImagePlugin.PngInfo()
    info.add_text("Comment", "saved from another app")
    Image.new("RGB", (10, 10), "red").save(folder / name, pnginfo=info)
    return folder / name


@pytest.mark.parametrize("copy", ["identical", "other metadata"])
def test_a_copy_in_a_folder_holding_the_hash_name_is_deleted(
    client: TestClient, db: sqlite3.Connection, image_dir: Path, copy: str
) -> None:
    if copy == "identical":
        shutil.copy(image_dir / "a.png", image_dir / "a (1).png")
    else:
        _tagged(image_dir, "a (1).png")
    source_id, _ = scan_source(client, image_dir)
    client.patch(f"/api/v1/sources/{source_id}", json={"writable": True})
    h = client.get("/api/v1/images", params={"source_id": source_id}).json()["items"][0]["content_hash"]
    versions = db.execute("SELECT COUNT(*) FROM file_metadata WHERE content_hash = ?", (h,))

    resp = _rename(client, h)

    assert resp.json() == {"renamed": 1, "deleted": 1, "kept_sidecars": [], "failed": []}
    assert _files(image_dir) == {f"{h}.png", "b.jpg", str(Path("sub") / "c.png"), "readme.txt"}
    assert [c["relative_path"] for c in client.get(f"/api/v1/images/{h}/copies").json()] == [
        f"{h}.png"
    ]
    # The deleted copy's metadata stays with the image.
    assert db.execute(
        "SELECT COUNT(*) FROM file_metadata WHERE content_hash = ?", (h,)
    ).fetchone()[0] == versions.fetchone()[0]


def test_a_read_only_source_refuses_the_whole_rename(
    client: TestClient, image_dir: Path, tmp_path: Path, writable: tuple[int, dict[str, str]]
) -> None:
    _, hashes = writable
    other = tmp_path / "other"
    other.mkdir()
    shutil.copy(image_dir / "a.png", other / "a.png")
    scan_source(client, other)

    resp = _rename(client, hashes["a.png"])

    assert resp.status_code == 409
    assert (image_dir / "a.png").exists()
    assert (other / "a.png").exists()


def test_a_file_changed_since_the_scan_refuses_the_whole_rename(
    client: TestClient, image_dir: Path, writable: tuple[int, dict[str, str]]
) -> None:
    _, hashes = writable
    shutil.copy(image_dir / "a.png", image_dir / "sub" / "a.png")
    client.post("/api/v1/sources/1/scan")
    client.get("/api/v1/sources/1/scan/status")
    os.utime(image_dir / "sub" / "a.png", (0, 0))

    resp = _rename(client, hashes["a.png"])

    assert resp.status_code == 409
    assert "changed since the last scan" in resp.json()["detail"]
    assert (image_dir / "a.png").exists()


def test_a_hash_name_taken_by_another_file_refuses_the_whole_rename(
    client: TestClient, image_dir: Path, writable: tuple[int, dict[str, str]]
) -> None:
    _, hashes = writable
    h = hashes["a.png"]
    (image_dir / f"{h}.png").write_text("not this image")

    resp = _rename(client, h)

    assert resp.status_code == 409
    assert (image_dir / "a.png").exists()
    assert (image_dir / f"{h}.png").read_text() == "not this image"


def test_sidecars_take_the_new_name(
    client: TestClient, db: sqlite3.Connection, image_dir: Path
) -> None:
    (image_dir / "a.txt").write_text("Steps: 20")
    (image_dir / "a.png.json").write_text("{}")
    source_id, _ = scan_source(client, image_dir)
    client.patch(f"/api/v1/sources/{source_id}", json={"writable": True})
    h = client.get("/api/v1/images", params={"source_id": source_id}).json()["items"][0]["content_hash"]

    _rename(client, h)

    assert {f"{h}.png", f"{h}.txt", f"{h}.png.json"} <= _files(image_dir)
    assert not {"a.txt", "a.png.json"} & _files(image_dir)
    assert {r[0] for r in db.execute("SELECT relative_path FROM sidecars")} >= {
        f"{h}.txt", f"{h}.png.json"
    }


def test_a_sidecar_another_file_is_named_after_stays(
    client: TestClient, image_dir: Path
) -> None:
    Image.new("RGB", (10, 10), "white").save(image_dir / "a.jpg")
    (image_dir / "a.txt").write_text("shared")
    source_id, _ = scan_source(client, image_dir)
    client.patch(f"/api/v1/sources/{source_id}", json={"writable": True})
    items = client.get("/api/v1/images", params={"source_id": source_id}).json()["items"]
    h = next(i["content_hash"] for i in items if i["filename"] == "a.png")

    _rename(client, h)

    assert (image_dir / "a.txt").read_text() == "shared"
    assert not (image_dir / f"{h}.txt").exists()


@pytest.mark.parametrize(
    ("kept", "redundant", "left"),
    [
        (None, "from the copy", {"a (1).txt": False, "HASH.txt": "from the copy"}),
        ("same", "same", {"a (1).txt": False, "HASH.txt": "same"}),
        ("kept's", "copy's", {"a (1).txt": "copy's", "HASH.txt": "kept's"}),
    ],
    ids=["moved to the free name", "deleted when the same", "left when different"],
)
def test_a_redundant_copys_sidecar(
    client: TestClient,
    image_dir: Path,
    kept: str | None,
    redundant: str,
    left: dict[str, str | bool],
) -> None:
    h = picture_hash(image_dir / "a.png")
    shutil.move(image_dir / "a.png", image_dir / f"{h}.png")
    shutil.copy(image_dir / f"{h}.png", image_dir / "a (1).png")
    if kept is not None:
        (image_dir / f"{h}.txt").write_text(kept)
    (image_dir / "a (1).txt").write_text(redundant)
    source_id, _ = scan_source(client, image_dir)
    client.patch(f"/api/v1/sources/{source_id}", json={"writable": True})

    resp = _rename(client, h)

    assert resp.json()["deleted"] == 1
    assert resp.json()["kept_sidecars"] == (["a (1).txt"] if "a (1).txt" in _files(image_dir) else [])
    for name, content in left.items():
        path = image_dir / name.replace("HASH", h)
        assert (path.read_text() if path.exists() else False) == content
