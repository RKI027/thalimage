"""In-app documentation endpoints."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from thalimage.deps import DocSlug, get_docs_dir
from thalimage.services.docs_service import PageDetail, PageSummary, get_page, list_pages

router = APIRouter(prefix="/docs", tags=["docs"])


@router.get("", response_model=list[PageSummary])
def get_docs(docs_dir: Path = Depends(get_docs_dir)) -> list[PageSummary]:
    return [PageSummary(slug=p.slug, title=p.title) for p in list_pages(docs_dir)]


@router.get("/{slug}", response_model=PageDetail)
def get_doc(
    slug: DocSlug,
    docs_dir: Path = Depends(get_docs_dir),
) -> PageDetail:
    try:
        page = get_page(docs_dir, slug)
    except KeyError:
        raise HTTPException(404, "Documentation page not found") from None
    return PageDetail(slug=page.slug, title=page.title, markdown=page.markdown)
