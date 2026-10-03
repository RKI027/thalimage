"""Metadata extraction for images including AI generation parameters."""

import json
from pathlib import Path
from typing import Any, Optional

import piexif  # type: ignore[import-untyped]
from PIL import Image
from pydantic import BaseModel
from sd_parsers import ParserManager  # type: ignore[import-untyped]


class ImageFileInfo(BaseModel):
    filename: str
    file_size: int
    format: str
    width: int
    height: int
    aspect_ratio: float
    modified: float
    created: Optional[float] = None


class AIParameters(BaseModel):
    tool: Optional[str] = None
    prompt: Optional[str] = None
    negative_prompt: Optional[str] = None
    raw_params: Optional[str] = None


class ImageMetadata(BaseModel):
    file_info: ImageFileInfo
    ai_params: Optional[AIParameters] = None
    exif_data: Optional[dict[str, Any]] = None
    png_text: Optional[dict[str, str]] = None


_parser_manager = ParserManager()

# Bump when extraction changes in a way existing rows should pick up: a
# scan re-reads files whose metadata row has an older version.
# 1: AI parameters read from sd-parsers' actual PromptInfo attributes.
EXTRACTOR_VERSION = 1


def extract_metadata(image_path: Path) -> ImageMetadata:
    """Extract all available metadata from an image file."""
    file_info = _extract_file_info(image_path)
    ai_params = _extract_ai_params(image_path)
    exif_data = _extract_exif(image_path)
    png_text = _extract_png_text(image_path)

    return ImageMetadata(
        file_info=file_info,
        ai_params=ai_params,
        exif_data=exif_data,
        png_text=png_text,
    )


def _extract_file_info(image_path: Path) -> ImageFileInfo:
    stat = image_path.stat()
    with Image.open(image_path) as img:
        return ImageFileInfo(
            filename=image_path.name,
            file_size=stat.st_size,
            format=img.format or "UNKNOWN",
            width=img.width,
            height=img.height,
            aspect_ratio=img.width / img.height if img.height > 0 else 1.0,
            modified=stat.st_mtime,
            created=getattr(stat, "st_birthtime", None),
        )


def _extract_ai_params(image_path: Path) -> Optional[AIParameters]:
    try:
        with Image.open(image_path) as img:
            prompt_info = _parser_manager.parse(img)
            if prompt_info:
                # sd-parsers' PromptInfo: generator is an enum, prompts are
                # joined into full_prompt / full_negative_prompt, and the
                # chunks it parsed are in raw_parameters (a dict).
                generator = prompt_info.generator
                raw = prompt_info.raw_parameters
                return AIParameters(
                    tool=str(getattr(generator, "value", generator)) if generator else None,
                    prompt=prompt_info.full_prompt or None,
                    negative_prompt=prompt_info.full_negative_prompt or None,
                    raw_params=raw if isinstance(raw, str) or raw is None else json.dumps(raw),
                )
    except Exception:
        pass
    return None


def _extract_exif(image_path: Path) -> Optional[dict[str, Any]]:
    try:
        exif_dict = piexif.load(str(image_path))
        readable: dict[str, Any] = {}
        for ifd_name in exif_dict:
            ifd_data = exif_dict[ifd_name]
            if not ifd_data or not isinstance(ifd_data, dict):
                continue
            section: dict[str, Any] = {}
            for tag_id, value in ifd_data.items():
                if isinstance(value, bytes):
                    try:
                        value = value.decode("utf-8")
                    except UnicodeDecodeError:
                        value = repr(value)
                section[str(tag_id)] = value
            if section:
                readable[str(ifd_name)] = section
        return readable or None
    except Exception:
        return None


def _extract_png_text(image_path: Path) -> Optional[dict[str, str]]:
    if image_path.suffix.lower() != ".png":
        return None
    try:
        with Image.open(image_path) as img:
            text_data = getattr(img, "text", None)
            if text_data:
                return dict(text_data)
    except Exception:
        pass
    return None
