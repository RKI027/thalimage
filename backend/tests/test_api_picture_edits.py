"""The possible edits of an image, through the API."""

from pathlib import Path

from fastapi.testclient import TestClient

from tests.helpers import scan_source
from tests.test_picture_edits import _crop, _picture


def _rescan(client: TestClient, source_id: int) -> list[str]:
    client.post(f"/api/v1/sources/{source_id}/scan")
    client.get(f"/api/v1/sources/{source_id}/scan/status")
    items = client.get("/api/v1/images", params={"source_id": source_id}).json()["items"]
    return [i["content_hash"] for i in items]


def _edited(client: TestClient, tmp_path: Path) -> tuple[int, str, str]:
    """A folder holding a.png, cropped in place after its first scan, and
    b.png, unchanged: the source, and a.png's old and new keys."""
    folder = tmp_path / "pics"
    folder.mkdir()
    _picture(folder / "a.png")
    _picture(folder / "b.png", (-0.8, 0, -0.4, 0.4))
    source_id, (old, _) = scan_source(client, folder)
    _crop(folder / "a.png")
    new = _rescan(client, source_id)[0]
    return source_id, old, new


def test_an_image_shows_the_picture_it_may_be_an_edit_of(client: TestClient, tmp_path: Path) -> None:
    _, old, new = _edited(client, tmp_path)

    edit = client.get(f"/api/v1/images/{new}").json()["possible_edit"]

    assert edit["old_hash"] == old
    assert client.get(f"/api/v1/images/{old}/thumb").status_code == 200


def test_an_image_with_no_possible_edit_shows_none(client: TestClient, tmp_path: Path) -> None:
    folder = tmp_path / "pics"
    folder.mkdir()
    _picture(folder / "a.png")
    _, (h,) = scan_source(client, folder)

    assert client.get(f"/api/v1/images/{h}").json()["possible_edit"] is None


def test_the_possible_edits_filter_lists_only_them(client: TestClient, tmp_path: Path) -> None:
    source_id, _, new = _edited(client, tmp_path)

    items = client.get(
        "/api/v1/images", params={"source_id": source_id, "possible_edits": True}
    ).json()["items"]

    assert [i["content_hash"] for i in items] == [new]


def test_merging_a_possible_edit(client: TestClient, tmp_path: Path) -> None:
    _, old, new = _edited(client, tmp_path)

    resp = client.post(f"/api/v1/images/{new}/possible-edit", json={"decision": "merge"})

    assert resp.status_code == 200
    assert resp.json()["possible_edit"] is None
    assert client.get(f"/api/v1/images/{old}/thumb").status_code == 404


def test_keeping_a_possible_edit_separate(client: TestClient, tmp_path: Path) -> None:
    _, old, new = _edited(client, tmp_path)

    resp = client.post(f"/api/v1/images/{new}/possible-edit", json={"decision": "separate"})

    assert resp.json()["possible_edit"] is None
    assert client.get(f"/api/v1/images/{old}/thumb").status_code == 200


def test_deciding_on_an_image_with_no_possible_edit_is_404(
    client: TestClient, tmp_path: Path
) -> None:
    folder = tmp_path / "pics"
    folder.mkdir()
    _picture(folder / "a.png")
    _, (h,) = scan_source(client, folder)

    resp = client.post(f"/api/v1/images/{h}/possible-edit", json={"decision": "merge"})
    assert resp.status_code == 404
