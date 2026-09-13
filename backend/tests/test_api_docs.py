"""Tests for the in-app documentation endpoints."""

from fastapi.testclient import TestClient


def test_list_docs_returns_titled_pages(client: TestClient) -> None:
    resp = client.get("/api/v1/docs")
    assert resp.status_code == 200
    pages = resp.json()
    assert len(pages) > 0
    for page in pages:
        assert page["slug"]
        assert page["title"]


def test_list_docs_is_ordered_by_filename_prefix(client: TestClient) -> None:
    """Numeric prefixes order the nav; they are not part of the slug."""
    pages = client.get("/api/v1/docs").json()
    slugs = [p["slug"] for p in pages]
    assert slugs == sorted(slugs, key=lambda s: [p["slug"] for p in pages].index(s))
    for slug in slugs:
        assert not slug[0].isdigit()


def test_elo_page_is_published(client: TestClient) -> None:
    slugs = {p["slug"] for p in client.get("/api/v1/docs").json()}
    assert "elo" in slugs


def test_get_doc_returns_markdown(client: TestClient) -> None:
    resp = client.get("/api/v1/docs/elo")
    assert resp.status_code == 200
    body = resp.json()
    assert body["slug"] == "elo"
    assert body["markdown"].startswith("# ")
    assert body["title"] == body["markdown"].splitlines()[0].removeprefix("# ").strip()


def test_get_doc_not_found(client: TestClient) -> None:
    assert client.get("/api/v1/docs/nope").status_code == 404


def test_get_doc_rejects_path_traversal(client: TestClient) -> None:
    """A slug must never address a file outside the docs directory."""
    for slug in ("../config", "..%2Fconfig", "a/b"):
        resp = client.get(f"/api/v1/docs/{slug}")
        assert "markdown" not in resp.text, slug
