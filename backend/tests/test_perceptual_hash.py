"""The perceptual hash: what a picture looks like, close for near-identical
pictures whatever their bytes."""

from pathlib import Path

from PIL import Image, ImageEnhance

from thalimage.core.perceptual_hash import distance, perceptual_hash

# The distance at or under which two pictures count as the same.
SAME = 0.15


def _picture(path: Path, extent: tuple[float, float, float, float] = (-2, -1.5, 1, 1.5)) -> Image.Image:
    img = Image.effect_mandelbrot((256, 256), extent, 100).convert("RGB")
    img.save(path)
    return img


def test_a_resized_re_encoded_copy_is_the_same_picture(tmp_path: Path) -> None:
    img = _picture(tmp_path / "a.png")
    img.resize((128, 128)).save(tmp_path / "b.jpg", quality=60)

    assert distance(perceptual_hash(tmp_path / "a.png"), perceptual_hash(tmp_path / "b.jpg")) <= SAME


def test_a_colour_adjusted_copy_is_the_same_picture(tmp_path: Path) -> None:
    img = _picture(tmp_path / "a.png")
    ImageEnhance.Color(ImageEnhance.Brightness(img).enhance(1.2)).enhance(1.5).save(tmp_path / "b.png")

    assert distance(perceptual_hash(tmp_path / "a.png"), perceptual_hash(tmp_path / "b.png")) <= SAME


def test_a_different_picture_is_not(tmp_path: Path) -> None:
    _picture(tmp_path / "a.png")
    _picture(tmp_path / "b.png", (-0.8, 0, -0.4, 0.4))

    assert distance(perceptual_hash(tmp_path / "a.png"), perceptual_hash(tmp_path / "b.png")) > 0.3


def test_identical_pictures_are_at_distance_zero(tmp_path: Path) -> None:
    _picture(tmp_path / "a.png")
    assert distance(perceptual_hash(tmp_path / "a.png"), perceptual_hash(tmp_path / "a.png")) == 0


def test_a_picture_with_transparency_or_a_palette_is_hashed(tmp_path: Path) -> None:
    img = _picture(tmp_path / "a.png")
    img.convert("RGBA").save(tmp_path / "rgba.png")
    img.convert("P", palette=Image.Palette.ADAPTIVE).save(tmp_path / "palette.gif")

    for name in ("rgba.png", "palette.gif"):
        assert distance(perceptual_hash(tmp_path / "a.png"), perceptual_hash(tmp_path / name)) <= SAME


def test_the_hash_fits_a_sqlite_integer(tmp_path: Path) -> None:
    _picture(tmp_path / "a.png")
    assert -(2**63) <= perceptual_hash(tmp_path / "a.png") < 2**63
