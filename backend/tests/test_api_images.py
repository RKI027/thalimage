"""Tests for /api/v1/images endpoints."""

import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient


from tests.helpers import ensure_source, insert_image, scan_source


def test_list_images_empty(client: TestClient) -> None:
    resp = client.get("/api/v1/images")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total_count"] == 0
    assert data["next_cursor"] is None


def test_list_images_after_scan(client: TestClient, image_dir: Path) -> None:
    hashes = scan_source(client, image_dir)[1]
    assert len(hashes) == 3

    resp = client.get("/api/v1/images")
    data = resp.json()
    assert data["total_count"] == 3
    assert len(data["items"]) == 3


def test_list_images_pagination(client: TestClient, image_dir: Path) -> None:
    scan_source(client, image_dir)[1]

    resp = client.get("/api/v1/images?limit=2")
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["next_cursor"] is not None

    resp2 = client.get(f"/api/v1/images?limit=2&cursor={data['next_cursor']}")
    data2 = resp2.json()
    assert len(data2["items"]) == 1
    assert data2["next_cursor"] is None


def test_pagination_covers_all_items_for_each_sort(
    client: TestClient, image_dir: Path
) -> None:
    """Paging one item at a time must visit every image exactly once, for any sort."""
    all_hashes = set(scan_source(client, image_dir)[1])
    assert len(all_hashes) == 3

    for sort in ("name", "date_modified", "date_created", "size", "aspect_ratio"):
        seen: list[str] = []
        cursor: str | None = None
        for _ in range(10):  # generous guard against an infinite loop
            params = {"limit": 1, "sort": sort}
            if cursor:
                params["cursor"] = cursor
            data = client.get("/api/v1/images", params=params).json()
            seen.extend(i["content_hash"] for i in data["items"])
            cursor = data["next_cursor"]
            if cursor is None:
                break
        assert sorted(seen) == sorted(all_hashes), f"sort={sort} dropped/duplicated rows"
        assert len(seen) == len(set(seen)), f"sort={sort} returned duplicates"


def test_list_images_sort_desc(client: TestClient, image_dir: Path) -> None:
    scan_source(client, image_dir)[1]

    asc = client.get("/api/v1/images?sort=name&dir=asc").json()
    desc = client.get("/api/v1/images?sort=name&dir=desc").json()
    asc_names = [i["filename"] for i in asc["items"]]
    desc_names = [i["filename"] for i in desc["items"]]
    assert asc_names == list(reversed(desc_names))


def test_get_image_detail(client: TestClient, image_dir: Path) -> None:
    hashes = scan_source(client, image_dir)[1]

    resp = client.get(f"/api/v1/images/{hashes[0]}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["content_hash"] == hashes[0]
    assert "width" in data
    assert "height" in data


ABSENT_HASH = "0" * 64  # well-formed SHA-256 hex that isn't in the DB


def test_get_image_not_found(client: TestClient) -> None:
    resp = client.get(f"/api/v1/images/{ABSENT_HASH}")
    assert resp.status_code == 404


def test_get_image_malformed_hash_rejected(client: TestClient) -> None:
    resp = client.get("/api/v1/images/not-a-hash")
    assert resp.status_code == 422


def test_get_image_file(client: TestClient, image_dir: Path) -> None:
    hashes = scan_source(client, image_dir)[1]
    resp = client.get(f"/api/v1/images/{hashes[0]}/file")
    assert resp.status_code == 200
    assert len(resp.content) > 0


def test_get_image_thumb(client: TestClient, image_dir: Path) -> None:
    hashes = scan_source(client, image_dir)[1]
    resp = client.get(f"/api/v1/images/{hashes[0]}/thumb")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/webp"


def test_get_thumb_not_found(client: TestClient) -> None:
    resp = client.get(f"/api/v1/images/{ABSENT_HASH}/thumb")
    assert resp.status_code == 404


def test_archive_hides_from_gallery(client: TestClient, image_dir: Path) -> None:
    hashes = scan_source(client, image_dir)[1]
    target = hashes[0]

    resp = client.patch(f"/api/v1/images/{target}/archive", json={"archived": True})
    assert resp.status_code == 200
    assert resp.json()["archived"] is True

    resp = client.get("/api/v1/images")
    listed = [i["content_hash"] for i in resp.json()["items"]]
    assert target not in listed
    assert resp.json()["total_count"] == len(hashes) - 1


def test_archive_still_accessible_by_hash(client: TestClient, image_dir: Path) -> None:
    hashes = scan_source(client, image_dir)[1]
    target = hashes[0]

    client.patch(f"/api/v1/images/{target}/archive", json={"archived": True})

    resp = client.get(f"/api/v1/images/{target}")
    assert resp.status_code == 200
    assert resp.json()["archived"] is True


def test_unarchive_restores_to_gallery(client: TestClient, image_dir: Path) -> None:
    hashes = scan_source(client, image_dir)[1]
    target = hashes[0]

    client.patch(f"/api/v1/images/{target}/archive", json={"archived": True})
    client.patch(f"/api/v1/images/{target}/archive", json={"archived": False})

    resp = client.get("/api/v1/images")
    listed = [i["content_hash"] for i in resp.json()["items"]]
    assert target in listed
    assert resp.json()["total_count"] == len(hashes)


def test_archive_not_found(client: TestClient) -> None:
    resp = client.patch(f"/api/v1/images/{ABSENT_HASH}/archive", json={"archived": True})
    assert resp.status_code == 404


def test_filter_by_aspect_ratio_square(client: TestClient, image_dir: Path) -> None:
    scan_source(client, image_dir)[1]
    # a.png (10x10) and c.png (5x5) are square; b.jpg (20x15) is landscape
    resp = client.get("/api/v1/images?aspect_ratio_filter=square")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_count"] == 2
    assert all(abs(i["aspect_ratio"] - 1.0) < 0.2 for i in data["items"])


def test_filter_by_aspect_ratio_landscape(client: TestClient, image_dir: Path) -> None:
    scan_source(client, image_dir)[1]
    # b.jpg (20x15, aspect_ratio ~1.33) is landscape
    resp = client.get("/api/v1/images?aspect_ratio_filter=landscape")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_count"] == 1
    assert data["items"][0]["filename"] == "b.jpg"


def _seed_media(db: sqlite3.Connection) -> dict[str, str]:
    """Two stills and a video, modified on consecutive days around a month end."""
    return {
        "jan30": insert_image(db, "a" * 64, file_modified="2024-01-30T23:59:59+00:00"),
        "jan31": insert_image(
            db, "b" * 64, filename="clip.mp4", format="MP4",
            file_modified="2024-01-31T10:00:00+00:00",
        ),
        "feb01": insert_image(db, "c" * 64, file_modified="2024-02-01T00:00:00+00:00"),
    }


def _listed(client: TestClient, **params: str) -> set[str]:
    resp = client.get("/api/v1/images", params=params)
    assert resp.status_code == 200
    return {i["content_hash"] for i in resp.json()["items"]}


def test_filter_by_media_type(client: TestClient, db: sqlite3.Connection) -> None:
    m = _seed_media(db)
    assert _listed(client, media_type="video") == {m["jan31"]}
    assert _listed(client, media_type="image") == {m["jan30"], m["feb01"]}


def test_filter_by_date_range(client: TestClient, db: sqlite3.Connection) -> None:
    m = _seed_media(db)
    assert _listed(client, date_from="2024-01-31") == {m["jan31"], m["feb01"]}
    assert _listed(client, date_to="2024-01-31") == {m["jan30"], m["jan31"]}


def test_single_day_range_includes_that_day(client: TestClient, db: sqlite3.Connection) -> None:
    """GEN-012: date_to is a whole day, not its first instant."""
    m = _seed_media(db)
    assert _listed(client, date_from="2024-01-31", date_to="2024-01-31") == {m["jan31"]}


def test_date_to_with_a_time_is_exact(client: TestClient, db: sqlite3.Connection) -> None:
    m = _seed_media(db)
    assert _listed(client, date_to="2024-01-31T09:00:00+00:00") == {m["jan30"]}


def test_get_image_preview_returns_webp(client: TestClient, image_dir: Path) -> None:
    hashes = scan_source(client, image_dir)[1]
    resp = client.get(f"/api/v1/images/{hashes[0]}/preview")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/webp"
    assert len(resp.content) > 0


def test_preview_size_snaps_to_a_bucket(client: TestClient, image_dir: Path) -> None:
    hashes = scan_source(client, image_dir)[1]
    resp = client.get(f"/api/v1/images/{hashes[0]}/preview", params={"size": 1000})
    assert resp.status_code == 200
    assert resp.headers["x-preview-size"] == "1280"


def test_preview_above_the_largest_bucket_gets_the_largest(
    client: TestClient, image_dir: Path
) -> None:
    """GEN-004: a 1512px-wide window at dpr 2 asks for 3024."""
    hashes = scan_source(client, image_dir)[1]
    for size in (2561, 3024, 5000):
        resp = client.get(f"/api/v1/images/{hashes[0]}/preview", params={"size": size})
        assert resp.status_code == 200, size
        assert resp.headers["x-preview-size"] == "2560"


def test_preview_rejects_an_absurd_size(client: TestClient, image_dir: Path) -> None:
    hashes = scan_source(client, image_dir)[1]
    resp = client.get(f"/api/v1/images/{hashes[0]}/preview", params={"size": 99999})
    assert resp.status_code == 422


def test_preview_not_found(client: TestClient) -> None:
    resp = client.get(f"/api/v1/images/{ABSENT_HASH}/preview")
    assert resp.status_code == 404


def test_preview_rejects_a_video(
    client: TestClient, db: sqlite3.Connection, tmp_path: Path
) -> None:
    root = tmp_path / "vids"
    root.mkdir()
    (root / "clip.mp4").write_bytes(b"not really a video")
    h = insert_image(
        db, "d" * 64, source_id=ensure_source(db, str(root)), filename="clip.mp4", format="MP4"
    )
    resp = client.get(f"/api/v1/images/{h}/preview")
    assert resp.status_code == 415


def test_immutable_cache_headers_on_served_files(
    client: TestClient, image_dir: Path
) -> None:
    """Content is addressed by hash, so responses never need revalidating."""
    hashes = scan_source(client, image_dir)[1]
    for route in ("file", "thumb", "preview"):
        resp = client.get(f"/api/v1/images/{hashes[0]}/{route}")
        assert resp.status_code == 200, route
        assert "immutable" in resp.headers["cache-control"], route


def test_malformed_cursor_is_400(client: TestClient, db: sqlite3.Connection) -> None:
    insert_image(db, "a" * 64)
    assert client.get("/api/v1/images", params={"cursor": "garbage"}).status_code == 400
    coll = client.post("/api/v1/collections", json={"name": "c"}).json()["id"]
    resp = client.get(
        "/api/v1/images",
        params={"cursor": "nan-ish|x", "sort": "elo", "collection_id": coll},
    )
    assert resp.status_code == 400


def test_neighbors_endpoint(client: TestClient, db: sqlite3.Connection) -> None:
    hashes = [insert_image(db, f"{i:064d}", filename=f"n{i}.png") for i in range(5)]
    resp = client.get(f"/api/v1/images/{hashes[2]}/neighbors", params={"window": 1})
    assert resp.status_code == 200
    data = resp.json()
    assert [i["content_hash"] for i in data["before"]] == [hashes[1]]
    assert [i["content_hash"] for i in data["after"]] == [hashes[3]]
    assert (data["position"], data["total_count"]) == (2, 5)

    preset = client.get("/api/v1/collections", params={"type": "source_preset"}).json()
    if not preset:  # insert_image does not create the preset; make it
        from thalimage.services.collection_service import get_or_create_source_preset

        get_or_create_source_preset(db, 1, "test")
        preset = client.get("/api/v1/collections", params={"type": "source_preset"}).json()
    resp = client.get(
        f"/api/v1/images/{hashes[0]}/neighbors", params={"collection_id": preset[0]["id"]}
    )
    assert resp.json()["total_count"] == 5

    assert client.get(f"/api/v1/images/{'f' * 64}/neighbors").status_code == 404
