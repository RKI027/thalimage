"""Videos iOS cannot play get a playable copy at scan time, which the
viewer plays; the original is never touched."""

import sqlite3
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from tests.helpers import requires_ffmpeg, scan_source
from thalimage.core.video import playable_copy_args, playable_copy_path, probe_streams
from thalimage.services.playable_copies import prepare_playable_copies


def _video(codec: str, tag: str = "", pix_fmt: str = "yuv420p") -> dict:
    return {"codec_type": "video", "codec_name": codec, "codec_tag_string": tag, "pix_fmt": pix_fmt}


def _audio(codec: str) -> dict:
    return {"codec_type": "audio", "codec_name": codec}


COVER = {"codec_type": "video", "codec_name": "mjpeg", "disposition": {"attached_pic": 1}}


@pytest.mark.parametrize(
    "ext, streams",
    [
        (".mp4", [_video("h264", "avc1"), _audio("aac")]),
        (".mp4", [_video("h264", "avc1", "yuvj420p")]),
        (".mov", [_video("hevc", "hvc1", "yuv420p10le"), _audio("mp3")]),
        (".mp4", [_video("av1", "av01"), _audio("aac")]),
    ],
)
def test_what_ios_plays_needs_no_copy(ext: str, streams: list[dict]) -> None:
    assert playable_copy_args(ext, streams) is None


@pytest.mark.parametrize(
    "ext, streams, args",
    [
        # The codecs are fine, the container is not: remux.
        (".mkv", [_video("h264"), _audio("aac"), COVER], ["-c:v", "copy", "-c:a", "copy"]),
        # HEVC needs the hvc1 tag.
        (".mp4", [_video("hevc", "hev1")], ["-c:v", "copy", "-tag:v", "hvc1"]),
        # Fine video, audio iOS may not play: convert the audio only.
        (".webm", [_video("av1"), _audio("opus")], ["-c:v", "copy", "-c:a", "aac", "-b:a", "160k"]),
    ],
)
def test_a_copy_reuses_what_ios_plays(ext: str, streams: list[dict], args: list[str]) -> None:
    assert playable_copy_args(ext, streams) == args


@pytest.mark.parametrize(
    "streams",
    [
        [_video("vp9"), _audio("opus")],
        [_video("vp8")],
        [_video("h264", "avc1", "yuv420p10le"), _audio("aac")],
        [_video("mpeg4", "FMP4"), _audio("mp3")],
    ],
)
def test_a_video_codec_ios_does_not_play_is_transcoded(streams: list[dict]) -> None:
    args = playable_copy_args(".mp4", streams)
    assert args is not None
    assert args[:2] == ["-c:v", "libx264"] and "yuv420p" in args


def _make_video(path: Path, video: list[str], audio: list[str] | None = None) -> Path:
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=64x48:rate=10:duration=1"]
    if audio:
        cmd += ["-f", "lavfi", "-i", "sine=duration=1", *audio]
    subprocess.run([*cmd, *video, str(path)], check=True, timeout=60)
    return path


def _codecs(path: Path) -> list[str]:
    return [s["codec_name"] for s in probe_streams(path)]


@pytest.fixture
def videos(image_dir: Path) -> Path:
    """A VP9/Opus WebM (iOS cannot play it) and an H.264 MP4 (it can)."""
    _make_video(image_dir / "vp9.webm", ["-c:v", "libvpx-vp9"], ["-c:a", "libopus"])
    _make_video(image_dir / "h264.mp4", ["-c:v", "libx264", "-pix_fmt", "yuv420p"])
    return image_dir


def _hash(client: TestClient, source_id: int, filename: str) -> str:
    items = client.get("/api/v1/images", params={"source_id": source_id}).json()["items"]
    return next(i["content_hash"] for i in items if i["filename"] == filename)


@requires_ffmpeg
def test_a_scan_makes_a_copy_only_of_what_ios_cannot_play(
    client: TestClient, videos: Path, video_dir: Path
) -> None:
    source_id, _ = scan_source(client, videos)
    webm, mp4 = _hash(client, source_id, "vp9.webm"), _hash(client, source_id, "h264.mp4")

    copy = playable_copy_path(video_dir, webm)
    assert copy.exists() and _codecs(copy) == ["h264", "aac"]
    assert not playable_copy_path(video_dir, mp4).exists()
    assert _codecs(videos / "vp9.webm") == ["vp9", "opus"]


@requires_ffmpeg
def test_the_viewer_plays_the_copy_or_else_the_original(
    client: TestClient, videos: Path, tmp_path: Path
) -> None:
    source_id, _ = scan_source(client, videos)

    for filename, served in (("vp9.webm", "h264"), ("h264.mp4", "h264")):
        resp = client.get(f"/api/v1/images/{_hash(client, source_id, filename)}/video")
        assert resp.status_code == 200
        out = tmp_path / f"served-{filename}"
        out.write_bytes(resp.content)
        assert _codecs(out)[0] == served
    original = client.get(f"/api/v1/images/{_hash(client, source_id, 'vp9.webm')}/file")
    assert original.content == (videos / "vp9.webm").read_bytes()


@requires_ffmpeg
def test_each_video_is_probed_once(
    client: TestClient, videos: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_id, _ = scan_source(client, videos)
    probed: list[Path] = []
    real_probe = probe_streams
    monkeypatch.setattr(
        "thalimage.services.playable_copies.probe_streams",
        lambda p: probed.append(p) or real_probe(p),
    )

    client.post(f"/api/v1/sources/{source_id}/scan")
    client.get(f"/api/v1/sources/{source_id}/scan/status")

    assert probed == []


@requires_ffmpeg
def test_checking_and_copying_report_their_progress(
    client: TestClient, db: sqlite3.Connection, videos: Path, video_dir: Path
) -> None:
    source_id, _ = scan_source(client, videos)
    db.execute("UPDATE images SET needs_playable_copy = NULL")
    db.commit()
    playable_copy_path(video_dir, _hash(client, source_id, "vp9.webm")).unlink()
    reports: list[dict] = []

    prepare_playable_copies(db, source_id, video_dir, progress_callback=lambda **kw: reports.append(kw))

    assert reports == [
        {"phase": "checking", "total": 2, "current": 0},
        {"current": 1},
        {"current": 2},
        {"phase": "converting", "total": 1, "current": 0},
        {"current": 1},
    ]


@requires_ffmpeg
def test_a_missing_copy_is_made_again(
    client: TestClient, videos: Path, video_dir: Path
) -> None:
    source_id, _ = scan_source(client, videos)
    copy = playable_copy_path(video_dir, _hash(client, source_id, "vp9.webm"))
    copy.unlink()

    client.post(f"/api/v1/sources/{source_id}/scan")
    client.get(f"/api/v1/sources/{source_id}/scan/status")

    assert copy.exists()


@requires_ffmpeg
def test_deleting_the_image_deletes_its_copy(
    client: TestClient, videos: Path, video_dir: Path
) -> None:
    source_id, _ = scan_source(client, videos)
    client.patch(f"/api/v1/sources/{source_id}", json={"writable": True})
    webm = _hash(client, source_id, "vp9.webm")

    client.post(f"/api/v1/images/{webm}/delete")

    assert not playable_copy_path(video_dir, webm).exists()


@requires_ffmpeg
def test_removing_the_source_deletes_its_copies(
    client: TestClient, videos: Path, video_dir: Path
) -> None:
    source_id, _ = scan_source(client, videos)
    webm = _hash(client, source_id, "vp9.webm")

    client.delete(f"/api/v1/sources/{source_id}", params={"keep_data": False})

    assert not playable_copy_path(video_dir, webm).exists()


@requires_ffmpeg
def test_a_copy_that_fails_leaves_the_video_indexed(
    client: TestClient, db: sqlite3.Connection, videos: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        raise RuntimeError("ffmpeg exploded")

    monkeypatch.setattr("thalimage.services.playable_copies.make_playable_copy", fail)
    source_id, _ = scan_source(client, videos)

    assert _hash(client, source_id, "vp9.webm")
    status = client.get(f"/api/v1/sources/{source_id}/scan/status").text
    assert '"errors":1' in status.replace(" ", "")


@requires_ffmpeg
def test_mkv_videos_are_scanned(client: TestClient, image_dir: Path) -> None:
    _make_video(image_dir / "clip.mkv", ["-c:v", "libx264", "-pix_fmt", "yuv420p"])

    source_id, _ = scan_source(client, image_dir)

    assert _hash(client, source_id, "clip.mkv")


def test_avif_images_are_scanned(client: TestClient, image_dir: Path) -> None:
    Image.new("RGB", (12, 8), "purple").save(image_dir / "pic.avif")

    source_id, _ = scan_source(client, image_dir)

    image = client.get(f"/api/v1/images/{_hash(client, source_id, 'pic.avif')}").json()
    assert (image["width"], image["height"]) == (12, 8)
    assert client.get(f"/api/v1/images/{image['content_hash']}/thumb").status_code == 200


@pytest.fixture
def video_dir(tmp_path: Path) -> Path:
    return tmp_path / "videos"



def _refuse(monkeypatch: pytest.MonkeyPatch, refused: Path) -> None:
    """Make checking whether `refused` exists fail, as an NFS mount can."""
    real_exists = Path.exists

    def exists(self: Path, *args: object, **kwargs: object) -> bool:
        if self == refused:
            raise PermissionError(13, "Permission denied", str(self))
        return real_exists(self)

    monkeypatch.setattr(Path, "exists", exists)


@requires_ffmpeg
def test_a_copy_that_cannot_be_checked_is_counted_and_the_others_made(
    client: TestClient,
    db: sqlite3.Connection,
    videos: Path,
    video_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _make_video(videos / "vp8.webm", ["-c:v", "libvpx"])
    source_id, _ = scan_source(client, videos)
    vp9, vp8 = _hash(client, source_id, "vp9.webm"), _hash(client, source_id, "vp8.webm")
    for h in (vp9, vp8):
        playable_copy_path(video_dir, h).unlink()
    db.execute("UPDATE images SET needs_playable_copy = NULL")
    db.commit()
    _refuse(monkeypatch, playable_copy_path(video_dir, vp9))

    errors = prepare_playable_copies(db, source_id, video_dir)

    assert errors == 1
    assert playable_copy_path(video_dir, vp8).is_file()
    probed = db.execute(
        "SELECT content_hash FROM images WHERE needs_playable_copy IS NOT NULL"
    ).fetchall()
    assert {vp9, vp8, _hash(client, source_id, "h264.mp4")} <= {r[0] for r in probed}


@requires_ffmpeg
def test_the_viewer_plays_the_original_when_the_copy_cannot_be_checked(
    client: TestClient, videos: Path, video_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_id, _ = scan_source(client, videos)
    webm = _hash(client, source_id, "vp9.webm")
    _refuse(monkeypatch, playable_copy_path(video_dir, webm))

    resp = client.get(f"/api/v1/images/{webm}/video")

    assert resp.status_code == 200
    assert resp.content == (videos / "vp9.webm").read_bytes()


@requires_ffmpeg
def test_deleting_several_images_deletes_their_copies(
    client: TestClient, videos: Path, video_dir: Path
) -> None:
    source_id, _ = scan_source(client, videos)
    client.patch(f"/api/v1/sources/{source_id}", json={"writable": True})
    webm = _hash(client, source_id, "vp9.webm")

    client.post("/api/v1/images/delete", json={"hashes": [webm]})

    assert not playable_copy_path(video_dir, webm).exists()
