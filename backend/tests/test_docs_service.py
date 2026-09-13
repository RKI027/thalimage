"""Tests for documentation page loading."""

from pathlib import Path

import pytest

from thalimage.services.docs_service import get_page, list_pages


def test_list_pages_strips_the_ordering_prefix(tmp_path: Path) -> None:
    (tmp_path / "10-second.md").write_text("# Second\n\nbody\n")
    (tmp_path / "01-first.md").write_text("# First\n\nbody\n")

    pages = list_pages(tmp_path)

    assert [p.slug for p in pages] == ["first", "second"]
    assert [p.title for p in pages] == ["First", "Second"]


def test_list_pages_ignores_non_markdown(tmp_path: Path) -> None:
    (tmp_path / "01-a.md").write_text("# A\n")
    (tmp_path / "notes.txt").write_text("ignored")

    assert [p.slug for p in list_pages(tmp_path)] == ["a"]


def test_title_falls_back_to_the_slug(tmp_path: Path) -> None:
    (tmp_path / "01-untitled.md").write_text("no heading here\n")

    assert list_pages(tmp_path)[0].title == "untitled"


def test_get_page_returns_the_markdown(tmp_path: Path) -> None:
    (tmp_path / "02-elo.md").write_text("# ELO\n\nHow pairs are picked.\n")

    page = get_page(tmp_path, "elo")

    assert page.title == "ELO"
    assert "How pairs are picked." in page.markdown


def test_get_page_raises_for_an_unknown_slug(tmp_path: Path) -> None:
    with pytest.raises(KeyError):
        get_page(tmp_path, "missing")


def test_get_page_refuses_to_escape_the_docs_directory(tmp_path: Path) -> None:
    (tmp_path.parent / "secret.md").write_text("# Secret\n")

    with pytest.raises(KeyError):
        get_page(tmp_path, "../secret")
