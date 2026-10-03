"""Service-level tests for image listing."""

import sqlite3

from tests.helpers import insert_image
from thalimage.services.image_service import list_images


def test_date_created_sort_pages_through_null_birthtimes(db: sqlite3.Connection) -> None:
    """Linux has no st_birthtime, so file_created is NULL there. The Created
    sort falls back to file_modified and must still page through every row,
    in both directions, mixed with rows that do have a birthtime."""
    rows = [
        ("a" * 64, "2024-01-03T00:00:00+00:00", None),
        ("b" * 64, "2024-01-01T00:00:00+00:00", None),
        ("c" * 64, "2024-01-09T00:00:00+00:00", "2024-01-02T00:00:00+00:00"),
        ("d" * 64, "2024-01-04T00:00:00+00:00", None),
    ]
    for h, modified, created in rows:
        insert_image(db, h, file_modified=modified, file_created=created)

    expected_asc = ["b" * 64, "c" * 64, "a" * 64, "d" * 64]
    for direction, expected in (("asc", expected_asc), ("desc", expected_asc[::-1])):
        seen: list[str] = []
        cursor = None
        for _ in range(10):
            page = list_images(
                db, sort="date_created", direction=direction, limit=1, cursor=cursor
            )
            seen.extend(i.content_hash for i in page.items)
            cursor = page.next_cursor
            if cursor is None:
                break
        assert seen == expected, direction


def test_grid_queries_use_an_index_for_every_sort(db: sqlite3.Connection) -> None:
    """GEN-016: no full scan + temp sort of images per page."""
    from thalimage.services import image_service

    captured: list[tuple[str, list[object]]] = []

    class Spy:
        def execute(self, sql: str, params: object = ()) -> sqlite3.Cursor:
            captured.append((sql, list(params)))  # type: ignore[call-overload]
            return db.execute(sql, params)  # type: ignore[arg-type]

    for sort in image_service.SORT_COLUMNS:
        list_images(Spy(), sort=sort, cursor="x|y")  # type: ignore[arg-type]
        sql, params = captured[-1]
        plan = " / ".join(r[3] for r in db.execute("EXPLAIN QUERY PLAN " + sql, params))
        assert "USING INDEX idx_images_live_" in plan, (sort, plan)
        assert "TEMP B-TREE" not in plan, (sort, plan)
