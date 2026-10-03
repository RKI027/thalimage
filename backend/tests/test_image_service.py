"""Service-level tests for image listing."""

import sqlite3

from thalimage.services.image_service import list_images


def test_date_created_sort_pages_through_null_birthtimes(db: sqlite3.Connection) -> None:
    """Linux has no st_birthtime, so file_created is NULL there. The Created
    sort falls back to file_modified and must still page through every row,
    in both directions, mixed with rows that do have a birthtime."""
    db.execute("INSERT INTO sources (path) VALUES ('/x')")
    rows = [
        ("a" * 64, "2024-01-03T00:00:00+00:00", None),
        ("b" * 64, "2024-01-01T00:00:00+00:00", None),
        ("c" * 64, "2024-01-09T00:00:00+00:00", "2024-01-02T00:00:00+00:00"),
        ("d" * 64, "2024-01-04T00:00:00+00:00", None),
    ]
    for h, modified, created in rows:
        db.execute(
            """INSERT INTO images (content_hash, filename, source_id, relative_path,
                   file_size, width, height, aspect_ratio, format,
                   file_modified, file_created, thumb_generated)
               VALUES (?, ?, 1, ?, 1, 1, 1, 1.0, 'PNG', ?, ?, 0)""",
            (h, f"{h}.png", f"{h}.png", modified, created),
        )
    db.commit()

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
