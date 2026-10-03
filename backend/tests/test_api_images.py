"""Tests for /api/v1/images endpoints."""

from pathlib import Path

from fastapi.testclient import TestClient


from tests.helpers import scan_source


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


def test_filter_by_media_type_image(client: TestClient, image_dir: Path) -> None:
    scan_source(client, image_dir)[1]
    resp = client.get("/api/v1/images?media_type=image")
    assert resp.status_code == 200
    # All test images are images (no videos in the fixture)
    assert resp.json()["total_count"] == 3


def test_filter_by_media_type_video(client: TestClient, image_dir: Path) -> None:
    scan_source(client, image_dir)[1]
    resp = client.get("/api/v1/images?media_type=video")
    assert resp.status_code == 200
    assert resp.json()["total_count"] == 0


def test_filter_by_date_from(client: TestClient, image_dir: Path) -> None:
    scan_source(client, image_dir)[1]
    # A future date should return no images
    resp = client.get("/api/v1/images?date_from=2099-01-01T00:00:00")
    assert resp.status_code == 200
    assert resp.json()["total_count"] == 0


def test_filter_by_date_to(client: TestClient, image_dir: Path) -> None:
    scan_source(client, image_dir)[1]
    # A past date should return no images
    resp = client.get("/api/v1/images?date_to=1970-01-01T00:00:00")
    assert resp.status_code == 200
    assert resp.json()["total_count"] == 0


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


def test_preview_rejects_an_absurd_size(client: TestClient, image_dir: Path) -> None:
    hashes = scan_source(client, image_dir)[1]
    resp = client.get(f"/api/v1/images/{hashes[0]}/preview", params={"size": 99999})
    assert resp.status_code == 422


def test_preview_not_found(client: TestClient) -> None:
    resp = client.get(f"/api/v1/images/{ABSENT_HASH}/preview")
    assert resp.status_code == 404


def test_preview_rejects_a_video(client: TestClient, tmp_path: Path) -> None:
    root = tmp_path / "vids"
    root.mkdir()
    (root / "clip.mp4").write_bytes(b"not really a video")
    hashes = scan_source(client, root)[1]
    if not hashes:
        return
    resp = client.get(f"/api/v1/images/{hashes[0]}/preview")
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
