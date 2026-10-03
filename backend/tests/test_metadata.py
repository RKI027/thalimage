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


# --- TST-003: extraction from real generator metadata ---

A1111_PARAMETERS = (
    "a castle on a hill, sunset\n"
    "Negative prompt: blurry, lowres\n"
    "Steps: 20, Sampler: Euler a, CFG scale: 7, Seed: 1234, Size: 8x8, Model: dreamshaper"
)

COMFY_PROMPT = {
    "3": {"class_type": "KSampler", "inputs": {
        "seed": 42, "steps": 20, "cfg": 7.0, "sampler_name": "euler",
        "scheduler": "normal", "denoise": 1.0, "model": ["4", 0],
        "positive": ["6", 0], "negative": ["7", 0], "latent_image": ["5", 0]}},
    "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "sdxl.safetensors"}},
    "5": {"class_type": "EmptyLatentImage", "inputs": {"width": 8, "height": 8, "batch_size": 1}},
    "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "a red fox in snow", "clip": ["4", 1]}},
    "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "watermark", "clip": ["4", 1]}},
    "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
    "9": {"class_type": "SaveImage", "inputs": {"images": ["8", 0], "filename_prefix": "x"}},
}


def _png_with_text(path: Path, **chunks: str) -> Path:
    from PIL import PngImagePlugin

    info = PngImagePlugin.PngInfo()
    for key, value in chunks.items():
        info.add_text(key, value)
    Image.new("RGB", (8, 8), "white").save(path, pnginfo=info)
    return path


def test_automatic1111_parameters(tmp_path: Path) -> None:
    import json

    path = _png_with_text(tmp_path / "a1111.png", parameters=A1111_PARAMETERS)
    ai = extract_metadata(path).ai_params
    assert ai is not None
    assert ai.tool == "AUTOMATIC1111"
    assert ai.prompt == "a castle on a hill, sunset"
    assert ai.negative_prompt == "blurry, lowres"
    assert ai.raw_params is not None
    assert json.loads(ai.raw_params) == {"parameters": A1111_PARAMETERS}


def test_comfyui_prompt_graph(tmp_path: Path) -> None:
    import json

    path = _png_with_text(
        tmp_path / "comfy.png",
        prompt=json.dumps(COMFY_PROMPT),
        workflow=json.dumps({"nodes": [], "links": []}),
    )
    ai = extract_metadata(path).ai_params
    assert ai is not None
    assert ai.tool == "ComfyUI"
    assert ai.prompt == "a red fox in snow"
    assert ai.negative_prompt == "watermark"
    assert ai.raw_params is not None and "KSampler" in ai.raw_params


def test_exif_user_comment_decodes_text_and_keeps_binary_readable(tmp_path: Path) -> None:
    import piexif  # type: ignore[import-untyped]

    exif = piexif.dump({
        "0th": {piexif.ImageIFD.Software: b"Thalimage Test"},
        "Exif": {piexif.ExifIFD.UserComment: b"\xff\xfe binary \x80"},
    })
    path = tmp_path / "with_exif.jpg"
    Image.new("RGB", (8, 8), "blue").save(path, format="JPEG", exif=exif)

    data = extract_metadata(path).exif_data
    assert data is not None
    assert data["0th"][str(piexif.ImageIFD.Software)] == "Thalimage Test"
    assert data["Exif"][str(piexif.ExifIFD.UserComment)] == repr(b"\xff\xfe binary \x80")
