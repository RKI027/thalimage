"""Documentation pages: Markdown files shipped alongside the app.

Files are named `NN-slug.md`; the numeric prefix orders the nav and is not
part of the slug. The title is the first level-1 heading.
"""

from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel


@dataclass(frozen=True)
class Page:
    slug: str
    title: str
    markdown: str


class PageSummary(BaseModel):
    slug: str
    title: str


class PageDetail(BaseModel):
    slug: str
    title: str
    markdown: str


def _slug_of(path: Path) -> str:
    stem = path.stem
    prefix, sep, rest = stem.partition("-")
    return rest if sep and prefix.isdigit() else stem


def _title_of(markdown: str, slug: str) -> str:
    for line in markdown.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return slug


def list_pages(docs_dir: Path) -> list[Page]:
    """All pages, ordered by filename so the numeric prefix drives the nav."""
    pages = []
    for path in sorted(docs_dir.glob("*.md")):
        markdown = path.read_text(encoding="utf-8")
        slug = _slug_of(path)
        pages.append(Page(slug=slug, title=_title_of(markdown, slug), markdown=markdown))
    return pages


def get_page(docs_dir: Path, slug: str) -> Page:
    """Look up one page by slug.

    Resolution goes through the listing rather than building a path from the
    slug, so a caller-supplied value can never address a file outside
    `docs_dir`.
    """
    for page in list_pages(docs_dir):
        if page.slug == slug:
            return page
    raise KeyError(slug)
