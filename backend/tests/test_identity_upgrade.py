"""Images identified by their picture hash: metadata edits, and the first
scan after upgrading from whole-file hashes (#106)."""

import os
import shutil
from pathlib import Path

import pytest

from thalimage.core.hasher import content_hash
from thalimage.core.picture_hash import picture_hash
from thalimage.core.previews import preview_path
from thalimage.core.thumbnails import thumbnail_path
from thalimage.core.video import playable_copy_path
from thalimage.db.engine import connect, migrate
from thalimage.services import scan_service
from thalimage.services.elo_service import get_rankings, record_vote
from thalimage.services.scan_service import run_scan
from thalimage.services.tag_service import add_image_tag, create_tag

FIXTURES = Path(__file__).parent / "fixtures" / "picture_hash"


class Library:
    """A database, one source folder and the cache folders."""

    def __init__(self, root: Path) -> None:
        self.folder = root / "photos"
        self.folder.mkdir()
        self.thumbs = root / "thumbs"
        self.previews = root / "previews"
        self.videos = root / "videos"
        self.conn = connect(root / "test.db")
        migrate(self.conn)
        self.conn.execute(
            "INSERT INTO sources (path, label) VALUES (?, 'photos')", (str(self.folder),)
        )
        self.conn.commit()
        self.source_id = 1

    def add(self, fixture: str, name: str | None = None) -> Path:
        path = self.folder / (name or fixture)
        shutil.copyfile(FIXTURES / fixture, path)
        return path

    def scan(self) -> scan_service.ScanResult:
        return run_scan(
            self.conn,
            self.source_id,
            self.thumbs,
            preview_dir=self.previews,
            video_dir=self.videos,
        )

    def scan_before_upgrade(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Scan as the app did when images were keyed by the whole-file hash."""
        with monkeypatch.context() as m:
            m.setattr(scan_service, "picture_hash", content_hash)
            m.setattr(scan_service, "HASH_VERSION", 0)
            self.scan()

    def live(self) -> dict[str, str]:
        """relative path -> image key, for every location of a live image."""
        return {
            r["relative_path"]: r["content_hash"]
            for r in self.conn.execute(
                "SELECT l.relative_path, l.content_hash FROM image_locations l"
                " JOIN images i ON i.content_hash = l.content_hash WHERE i.deleted = 0"
            )
        }

    def tags(self, key: str) -> set[str]:
        return {
            r[0]
            for r in self.conn.execute(
                "SELECT t.name FROM image_tags it JOIN tags t ON t.id = it.tag_id"
                " WHERE it.image_hash = ?",
                (key,),
            )
        }

    def tag(self, key: str, name: str) -> None:
        add_image_tag(self.conn, key, create_tag(self.conn, name).id)

    def collection(self, *keys: str) -> int:
        cur = self.conn.execute(
            "INSERT INTO collections (name) VALUES (?)", (f"Picked {len(keys)} {keys[0][:8]}",)
        )
        self.conn.executemany(
            "INSERT INTO collection_images (collection_id, content_hash) VALUES (?, ?)",
            [(cur.lastrowid, k) for k in keys],
        )
        self.conn.commit()
        return int(cur.lastrowid or 0)

    def members(self, collection_id: int) -> set[str]:
        return {
            r[0]
            for r in self.conn.execute(
                "SELECT content_hash FROM collection_images WHERE collection_id = ?",
                (collection_id,),
            )
        }

    def standings(self, collection_id: int) -> dict[str, tuple[float, int]]:
        return {
            r.image.content_hash: (round(r.score, 9), r.matches)
            for r in get_rankings(self.conn, collection_id).items
        }


@pytest.fixture
def library(tmp_path: Path) -> Library:
    return Library(tmp_path)


def test_an_image_is_keyed_by_its_picture_hash(library: Library) -> None:
    path = library.add("picture.jpg")
    library.scan()
    assert library.live() == {"picture.jpg": picture_hash(path)}


def test_writing_metadata_into_a_file_keeps_it_the_same_image(library: Library) -> None:
    library.add("picture.jpg")
    library.scan()
    (key,) = library.live().values()
    library.tag(key, "favourite")

    library.add("picture-tagged.jpg", "picture.jpg")
    library.scan()

    assert library.live() == {"picture.jpg": key}
    assert "favourite" in library.tags(key)


def test_upgrade_rekeys_an_unchanged_file_with_its_data(
    library: Library, monkeypatch: pytest.MonkeyPatch
) -> None:
    jpg, png = library.add("picture.jpg"), library.add("picture-other.png")
    library.scan_before_upgrade(monkeypatch)
    old, other = content_hash(jpg), content_hash(png)
    library.tag(old, "favourite")
    cid = library.collection(old, other)
    record_vote(library.conn, cid, winner_hash=old, loser_hash=other)
    before = library.standings(cid)

    library.scan()

    new = picture_hash(jpg)
    assert library.live()["picture.jpg"] == new
    assert library.conn.execute("SELECT 1 FROM images WHERE content_hash = ?", (old,)).fetchone() is None
    assert library.tags(new) == {"favourite"}
    assert library.members(cid) == {new, picture_hash(png)}
    renamed = {picture_hash(png) if k == other else new: v for k, v in before.items()}
    assert library.standings(cid) == renamed


def test_upgrade_moves_the_thumbnail_previews_and_playable_copy(
    library: Library, monkeypatch: pytest.MonkeyPatch
) -> None:
    jpg = library.add("picture.jpg")
    library.scan_before_upgrade(monkeypatch)
    old = content_hash(jpg)
    thumb_inode = thumbnail_path(library.thumbs, old).stat().st_ino
    for path in (preview_path(library.previews, old, 800), playable_copy_path(library.videos, old)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"cached " + path.suffix.encode())

    library.scan()

    new = picture_hash(jpg)
    assert thumbnail_path(library.thumbs, new).stat().st_ino == thumb_inode
    assert preview_path(library.previews, new, 800).read_bytes() == b"cached .webp"
    assert playable_copy_path(library.videos, new).read_bytes() == b"cached .mp4"
    for path in (
        thumbnail_path(library.thumbs, old),
        preview_path(library.previews, old, 800),
        playable_copy_path(library.videos, old),
    ):
        assert not path.exists()


def test_upgrade_merges_images_holding_the_same_picture(
    library: Library, monkeypatch: pytest.MonkeyPatch
) -> None:
    plain, tagged = library.add("picture.jpg"), library.add("picture-tagged.jpg")
    png = library.add("picture-other.png")
    library.scan_before_upgrade(monkeypatch)
    a, b, other = content_hash(plain), content_hash(tagged), content_hash(png)
    library.tag(a, "favourite")
    library.tag(b, "portfolio")
    cid = library.collection(a, b, other)
    record_vote(library.conn, cid, winner_hash=a, loser_hash=other)
    record_vote(library.conn, cid, winner_hash=a, loser_hash=b)
    record_vote(library.conn, cid, winner_hash=other, loser_hash=b)

    library.scan()

    merged, other_new = picture_hash(plain), picture_hash(png)
    assert library.live() == {
        "picture.jpg": merged,
        "picture-tagged.jpg": merged,
        "picture-other.png": other_new,
    }
    assert library.tags(merged) >= {"favourite", "portfolio"}
    assert library.members(cid) == {merged, other_new}
    # The vote between the two is dropped; the others replay in order.
    expected = library.collection(merged, other_new)
    record_vote(library.conn, expected, winner_hash=merged, loser_hash=other_new)
    record_vote(library.conn, expected, winner_hash=other_new, loser_hash=merged)
    assert library.standings(cid) == library.standings(expected)


def test_upgrade_treats_a_file_changed_since_the_last_scan_as_new(
    library: Library, monkeypatch: pytest.MonkeyPatch
) -> None:
    jpg = library.add("picture.jpg")
    library.scan_before_upgrade(monkeypatch)
    old = content_hash(jpg)
    library.tag(old, "favourite")
    library.add("picture-tagged.jpg", "picture.jpg")
    os.utime(jpg, (1, 1))

    library.scan()

    new = picture_hash(jpg)
    assert library.live() == {"picture.jpg": new}
    assert "favourite" not in library.tags(new)


def test_upgrade_reads_each_file_once(library: Library, monkeypatch: pytest.MonkeyPatch) -> None:
    library.add("picture.jpg")
    library.add("picture-other.png")
    library.scan_before_upgrade(monkeypatch)

    assert library.scan().added == 2
    assert library.scan().skipped == 2
