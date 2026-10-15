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


# --- Keywords and rating written by photo tools (XMP, IPTC, Windows EXIF) ---

def _xmp(*keywords: str, rating: str | None = None, rating_as_element: bool = False) -> bytes:
    """An XMP packet as Windows Explorer / Exiv2 write it."""
    attr = f' xmp:Rating="{rating}"' if rating is not None and not rating_as_element else ""
    elem = f"<xmp:Rating>{rating}</xmp:Rating>" if rating is not None and rating_as_element else ""
    items = "".join(f"<rdf:li>{k}</rdf:li>" for k in keywords)
    subject = f"<dc:subject><rdf:Bag>{items}</rdf:Bag></dc:subject>" if keywords else ""
    return (
        '<?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?>'
        '<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF'
        ' xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
        '<rdf:Description rdf:about="" xmlns:dc="http://purl.org/dc/elements/1.1/"'
        f' xmlns:xmp="http://ns.adobe.com/xap/1.0/"{attr}>{elem}{subject}'
        '</rdf:Description></rdf:RDF></x:xmpmeta><?xpacket end="w"?>'
    ).encode()


def _iptc_jpeg(path: Path, *keywords: str) -> Path:
    """A JPEG whose only keywords are IPTC ones, in a Photoshop APP13 block."""
    import io
    import struct

    iptc = b"".join(
        b"\x1c\x02\x19" + struct.pack(">H", len(k.encode())) + k.encode() for k in keywords
    )
    if len(iptc) % 2:
        iptc += b"\0"
    block = b"8BIM" + struct.pack(">H", 0x0404) + b"\0\0" + struct.pack(">I", len(iptc)) + iptc
    app13 = b"Photoshop 3.0\0" + block
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), "white").save(buf, format="JPEG")
    jpeg = buf.getvalue()
    path.write_bytes(jpeg[:2] + b"\xff\xed" + struct.pack(">H", len(app13) + 2) + app13 + jpeg[2:])
    return path


def test_plain_image_has_no_keywords_or_rating(sample_jpeg: Path) -> None:
    result = extract_metadata(sample_jpeg)
    assert (result.keywords, result.rating) == ([], None)


def test_jpeg_xmp_keywords_and_rating(tmp_path: Path) -> None:
    path = tmp_path / "x.jpg"
    Image.new("RGB", (8, 8)).save(path, format="JPEG", xmp=_xmp("stable diffusion", "beach", rating="5"))

    result = extract_metadata(path)
    assert result.keywords == ["stable diffusion", "beach"]
    assert result.rating == 5


def test_png_xmp_keywords(tmp_path: Path) -> None:
    from PIL import PngImagePlugin

    info = PngImagePlugin.PngInfo()
    info.add_itxt("XML:com.adobe.xmp", _xmp("castle", rating="3").decode())
    path = tmp_path / "x.png"
    Image.new("RGB", (8, 8)).save(path, pnginfo=info)

    result = extract_metadata(path)
    assert (result.keywords, result.rating) == (["castle"], 3)


def test_webp_xmp_keywords(tmp_path: Path) -> None:
    path = tmp_path / "x.webp"
    Image.new("RGB", (8, 8)).save(path, format="WEBP", xmp=_xmp("fox"))

    assert extract_metadata(path).keywords == ["fox"]


def test_xmp_rating_written_as_an_element(tmp_path: Path) -> None:
    path = tmp_path / "x.jpg"
    Image.new("RGB", (8, 8)).save(path, format="JPEG", xmp=_xmp(rating="4", rating_as_element=True))

    assert extract_metadata(path).rating == 4


def test_unrated_and_rejected_are_no_rating(tmp_path: Path) -> None:
    for value in ("0", "-1", "nonsense"):
        path = tmp_path / f"r{value}.jpg"
        Image.new("RGB", (8, 8)).save(path, format="JPEG", xmp=_xmp(rating=value))
        assert extract_metadata(path).rating is None


def test_keywords_are_trimmed_and_deduplicated(tmp_path: Path) -> None:
    path = tmp_path / "x.jpg"
    Image.new("RGB", (8, 8)).save(path, format="JPEG", xmp=_xmp(" fox ", "fox", "", "snow"))

    assert extract_metadata(path).keywords == ["fox", "snow"]


def test_malformed_xmp_is_ignored(tmp_path: Path) -> None:
    path = tmp_path / "x.jpg"
    Image.new("RGB", (8, 8)).save(path, format="JPEG", xmp=b"<x:xmpmeta not closed")

    result = extract_metadata(path)
    assert (result.keywords, result.rating) == ([], None)


def test_iptc_keywords_when_there_is_no_xmp(tmp_path: Path) -> None:
    path = _iptc_jpeg(tmp_path / "iptc.jpg", "stable diffusion", "café")

    assert extract_metadata(path).keywords == ["stable diffusion", "café"]


def test_windows_exif_rating_when_there_is_no_xmp(tmp_path: Path) -> None:
    import piexif  # type: ignore[import-untyped]

    path = tmp_path / "x.jpg"
    exif = piexif.dump({"0th": {piexif.ImageIFD.Rating: 4}})
    Image.new("RGB", (8, 8)).save(path, format="JPEG", exif=exif)

    assert extract_metadata(path).rating == 4
