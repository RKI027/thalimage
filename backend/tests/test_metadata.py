"""Tests for metadata extraction."""

from pathlib import Path

from PIL import Image
from pydantic import BaseModel

from thalimage.core.metadata import extract_metadata, ImageFileInfo


def test_extract_returns_file_info(sample_png: Path) -> None:
    result = extract_metadata(sample_png)
    assert isinstance(result.file_info, ImageFileInfo)
    assert result.file_info.width == 4
    assert result.file_info.height == 3
    assert result.file_info.format == "PNG"
    assert result.file_info.file_size > 0


def test_extract_jpeg(sample_jpeg: Path) -> None:
    result = extract_metadata(sample_jpeg)
    assert result.file_info.width == 8
    assert result.file_info.height == 6
    assert result.file_info.format == "JPEG"


def test_extract_ai_params_empty_for_plain_image(sample_png: Path) -> None:
    result = extract_metadata(sample_png)
    assert result.ai_params is None or result.ai_params.prompt is None


def test_extract_png_text_chunks(tmp_path: Path) -> None:
    """PNG with text chunks should be extracted."""
    from PIL import PngImagePlugin

    img = Image.new("RGB", (2, 2), "white")
    info = PngImagePlugin.PngInfo()
    info.add_text("Description", "test description")
    path = tmp_path / "with_text.png"
    img.save(path, pnginfo=info)

    result = extract_metadata(path)
    assert result.png_text is not None
    assert "Description" in result.png_text


def test_extract_returns_pydantic_models(sample_png: Path) -> None:
    result = extract_metadata(sample_png)
    assert isinstance(result, BaseModel)
    assert isinstance(result.file_info, BaseModel)
