"""Metadata extraction for images including AI generation parameters."""

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Optional

import piexif  # type: ignore[import-untyped]
from defusedxml import DefusedXmlException
from defusedxml.ElementTree import fromstring as parse_xml
from PIL import Image, ImageFile, IptcImagePlugin
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
    # What photo tools (Explorer, digiKam, Lightroom...) wrote into the file.
    keywords: list[str] = []
    rating: Optional[int] = None  # 1-5 stars; unrated and rejected are None


_parser_manager = ParserManager()

# Bump when extraction changes in a way existing rows should pick up: a
# scan re-reads files whose metadata row has an older version.
# 1: AI parameters read from sd-parsers' actual PromptInfo attributes.
# 2: keywords and star rating.
EXTRACTOR_VERSION = 2


def extract_metadata(image_path: Path) -> ImageMetadata:
    """Extract all available metadata from an image file."""
    file_info = _extract_file_info(image_path)
    ai_params = _extract_ai_params(image_path)
    exif_data = _extract_exif(image_path)
    png_text = _extract_png_text(image_path)
    keywords, rating = _extract_keywords_and_rating(image_path, exif_data)

    return ImageMetadata(
        file_info=file_info,
        ai_params=ai_params,
        exif_data=exif_data,
        png_text=png_text,
        keywords=keywords,
        rating=rating,
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


_RDF = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}"
_DC_SUBJECT = "{http://purl.org/dc/elements/1.1/}subject"
_XMP_RATING = "{http://ns.adobe.com/xap/1.0/}Rating"
_IPTC_KEYWORDS = (2, 25)
_EXIF_RATING = str(piexif.ImageIFD.Rating)  # Windows' star rating


def _extract_keywords_and_rating(
    image_path: Path, exif_data: Optional[dict[str, Any]]
) -> tuple[list[str], Optional[int]]:
    """Keywords and star rating, from XMP where the file has it. Tools
    write the same values in several standards at once; IPTC keywords and
    the Windows EXIF rating are read only when XMP lacks them."""
    keywords: list[str] = []
    rating: Optional[str] = None
    try:
        with Image.open(image_path) as img:
            xmp = _parse_xmp(img.info.get("xmp") or img.info.get("XML:com.adobe.xmp"))
            if xmp is not None:
                keywords = [
                    li.text or ""
                    for subject in xmp.iter(_DC_SUBJECT)
                    for li in subject.iter(f"{_RDF}li")
                ]
                rating = _xmp_rating(xmp)
            if not keywords:
                keywords = _iptc_keywords(img)
    except Exception:
        pass
    if rating is None and exif_data:
        rating = str(exif_data.get("0th", {}).get(_EXIF_RATING, "")) or None
    return _distinct(keywords), _stars(rating)


def _parse_xmp(packet: Any) -> Optional[ET.Element]:
    """Parse an XMP packet, refusing entity expansion and external
    references: it comes from files of unknown origin."""
    if not packet:
        return None
    try:
        root: ET.Element = parse_xml(packet.decode("utf-8") if isinstance(packet, bytes) else packet)
        return root
    except (ET.ParseError, DefusedXmlException, UnicodeDecodeError):
        return None


def _xmp_rating(xmp: ET.Element) -> Optional[str]:
    """xmp:Rating is written as an attribute of rdf:Description or as an
    element of its own."""
    for desc in xmp.iter(f"{_RDF}Description"):
        if _XMP_RATING in desc.attrib:
            return desc.attrib[_XMP_RATING]
    elem = next(xmp.iter(_XMP_RATING), None)
    return elem.text if elem is not None else None


def _iptc_keywords(img: ImageFile.ImageFile) -> list[str]:
    info = IptcImagePlugin.getiptcinfo(img) or {}
    values = info.get(_IPTC_KEYWORDS, [])
    if isinstance(values, bytes):
        values = [values]
    return [_decode(v) for v in values]


def _decode(value: bytes) -> str:
    try:
        return value.decode("utf-8")
    except UnicodeDecodeError:
        return value.decode("latin-1")


def _stars(value: Optional[str]) -> Optional[int]:
    try:
        stars = round(float(value)) if value is not None else 0
    except ValueError:
        return None
    return stars if 1 <= stars <= 5 else None


def _distinct(keywords: list[str]) -> list[str]:
    return list(dict.fromkeys(k.strip() for k in keywords if k.strip()))
