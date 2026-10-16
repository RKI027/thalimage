"""The picture hash: SHA-256 of the bytes that make up a file's picture or
video, leaving out the metadata stored beside them, so that writing
keywords, ratings or comments into a file does not change it.

The container is parsed, never decoded: decoders can disagree on pixels
across versions, while the stored bytes stay put. What counts as picture:

- PNG: the IHDR, PLTE, tRNS, IDAT and animation chunks.
- JPEG: every segment but the APPn and comment ones, with the scan data.
- WebP: the VP8, VP8L, ALPH, ANIM and ANMF chunks.
- TIFF: the strips or tiles of each image in the IFD chain.
- MP4, MOV and other ISO media with a movie box: the media data boxes.
- AVIF, HEIC and other HEIF images: every item but the Exif, XMP and URI
  ones; tools add metadata as items, sometimes inside the media data box.

Any other format, and any file whose structure does not hold together,
falls back to the whole-file hash.
"""

import hashlib
import mmap
import struct
from collections.abc import Iterator
from pathlib import Path
from typing import Optional

from thalimage.core.hasher import content_hash

# The version of what the picture hash covers. Raise it when that changes
# (a format gains a parser, a parser takes other bytes): scans then read
# every file again and re-key its image.
HASH_VERSION = 1

# A byte range of the file, [start, end).
Range = tuple[int, int]


class _Malformed(Exception):
    """The file does not have the structure its signature announces."""


def picture_hash(path: Path) -> str:
    """The SHA-256 hex digest of the file's picture data, or of the whole
    file when its format is not one parsed here or it is malformed."""
    try:
        with open(path, "rb") as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as data:
            ranges = _picture_ranges(data)
            if ranges is None:
                return content_hash(path)
            h = hashlib.sha256()
            for start, end in ranges:
                h.update(data[start:end])
            return h.hexdigest()
    except (_Malformed, ValueError, struct.error):
        # ValueError: an empty file (mmap), or TIFF offsets and counts
        # that do not pair up (zip).
        return content_hash(path)


def _picture_ranges(data: mmap.mmap) -> Optional[list[Range]]:
    """The ranges holding the picture, in order; None for a format that has
    no parser here."""
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        ranges = _png(data)
    elif data[:2] == b"\xff\xd8":
        ranges = _jpeg(data)
    elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        ranges = _webp(data)
    elif data[:4] in (b"II*\x00", b"MM\x00*"):
        ranges = _tiff(data)
    elif data[4:8] == b"ftyp":
        ranges = _iso_media(data)
    else:
        return None
    if not ranges:
        raise _Malformed("no picture data")
    for start, end in ranges:
        if not 0 <= start <= end <= len(data):
            raise _Malformed("range outside the file")
    return ranges


# --- PNG ---

_PNG_PICTURE_CHUNKS = {b"IHDR", b"PLTE", b"tRNS", b"IDAT", b"acTL", b"fcTL", b"fdAT"}


def _png(data: mmap.mmap) -> list[Range]:
    ranges: list[Range] = []
    off = 8
    while True:
        length, kind = struct.unpack(">I4s", data[off:off + 8])
        end = off + 12 + length  # length, type, data, CRC
        if end > len(data):
            raise _Malformed("PNG chunk past the end")
        if kind in _PNG_PICTURE_CHUNKS:
            ranges.append((off + 4, off + 8 + length))  # type and data
        if kind == b"IEND":
            return ranges
        off = end


# --- JPEG ---

_JPEG_EOI = 0xD9
_JPEG_SOS = 0xDA
_JPEG_COM = 0xFE


def _jpeg_is_metadata(marker: int) -> bool:
    return 0xE0 <= marker <= 0xEF or marker == _JPEG_COM


def _jpeg(data: mmap.mmap) -> list[Range]:
    ranges: list[Range] = []
    off = 2
    while True:
        if data[off] != 0xFF:
            raise _Malformed("JPEG marker expected")
        while data[off + 1] == 0xFF:  # fill bytes
            off += 1
        marker = data[off + 1]
        if marker == _JPEG_EOI:
            return ranges
        (length,) = struct.unpack(">H", data[off + 2:off + 4])
        end = off + 2 + length
        if end > len(data):
            raise _Malformed("JPEG segment past the end")
        if not _jpeg_is_metadata(marker):
            ranges.append((off, end))
        if marker == _JPEG_SOS:
            scan_end = _jpeg_scan_end(data, end)
            ranges.append((end, scan_end))
            end = scan_end
        off = end


def _jpeg_scan_end(data: mmap.mmap, off: int) -> int:
    """Where the entropy-coded data starting at `off` ends: the first marker
    that is neither a stuffed 0xFF nor a restart marker."""
    while True:
        off = data.find(b"\xff", off)
        if off < 0 or off + 1 >= len(data):
            raise _Malformed("JPEG scan without an end")
        following = data[off + 1]
        if following == 0x00 or 0xD0 <= following <= 0xD7:
            off += 2
        else:
            return off


# --- WebP ---

_WEBP_PICTURE_CHUNKS = {b"VP8 ", b"VP8L", b"ALPH", b"ANIM", b"ANMF"}


def _webp(data: mmap.mmap) -> list[Range]:
    ranges: list[Range] = []
    off = 12
    while off < len(data):
        kind, size = struct.unpack("<4sI", data[off:off + 8])
        end = off + 8 + size
        if end > len(data):
            raise _Malformed("WebP chunk past the end")
        if kind in _WEBP_PICTURE_CHUNKS:
            ranges.append((off, end))
        off = end + (size & 1)  # chunks are padded to an even size
    return ranges


# --- TIFF ---

_TIFF_STRIP_OFFSETS, _TIFF_STRIP_COUNTS = 273, 279
_TIFF_TILE_OFFSETS, _TIFF_TILE_COUNTS = 324, 325
_TIFF_VALUE_FORMATS = {3: "H", 4: "I"}  # SHORT, LONG


def _tiff(data: mmap.mmap) -> list[Range]:
    order = "<" if data[:2] == b"II" else ">"
    (ifd,) = struct.unpack(order + "I", data[4:8])
    ranges: list[Range] = []
    seen: set[int] = set()
    while ifd:
        if ifd in seen:
            raise _Malformed("TIFF IFD loop")
        seen.add(ifd)
        tags, ifd = _tiff_ifd(data, order, ifd)
        for offsets_tag, counts_tag in (
            (_TIFF_STRIP_OFFSETS, _TIFF_STRIP_COUNTS),
            (_TIFF_TILE_OFFSETS, _TIFF_TILE_COUNTS),
        ):
            offsets, counts = tags.get(offsets_tag), tags.get(counts_tag)
            if offsets is not None and counts is not None:
                ranges.extend((o, o + c) for o, c in zip(offsets, counts, strict=True))
    return ranges


def _tiff_ifd(data: mmap.mmap, order: str, off: int) -> tuple[dict[int, list[int]], int]:
    """The strip and tile tags of the IFD at `off`, and the next IFD's offset."""
    wanted = {_TIFF_STRIP_OFFSETS, _TIFF_STRIP_COUNTS, _TIFF_TILE_OFFSETS, _TIFF_TILE_COUNTS}
    (count,) = struct.unpack(order + "H", data[off:off + 2])
    tags: dict[int, list[int]] = {}
    for i in range(count):
        entry = off + 2 + 12 * i
        tag, kind, n = struct.unpack(order + "HHI", data[entry:entry + 8])
        if tag not in wanted:
            continue
        fmt = _TIFF_VALUE_FORMATS.get(kind)
        if fmt is None:
            raise _Malformed("TIFF offsets of an unexpected type")
        size = struct.calcsize(fmt) * n
        if size <= 4:
            at = entry + 8
        else:
            (at,) = struct.unpack(order + "I", data[entry + 8:entry + 12])
        if at + size > len(data):
            raise _Malformed("TIFF values past the end")
        tags[tag] = list(struct.unpack(f"{order}{n}{fmt}", data[at:at + size]))
    next_at = off + 2 + 12 * count
    (next_ifd,) = struct.unpack(order + "I", data[next_at:next_at + 4])
    return tags, next_ifd


# --- ISO base media (MP4, MOV, AVIF, HEIC) ---


def _boxes(data: mmap.mmap, start: int, end: int) -> Iterator[tuple[bytes, int, int]]:
    """The boxes in [start, end): type, payload start, box end."""
    off = start
    while off + 8 <= end:
        size, kind = struct.unpack(">I4s", data[off:off + 8])
        header = 8
        if size == 1:
            (size,) = struct.unpack(">Q", data[off + 8:off + 16])
            header = 16
        elif size == 0:
            size = end - off
        if size < header or off + size > end:
            raise _Malformed("box past its container")
        yield kind, off + header, off + size
        off += size
    if off != end:
        raise _Malformed("trailing bytes after the last box")


def _iso_media(data: mmap.mmap) -> list[Range]:
    top = list(_boxes(data, 0, len(data)))
    if any(kind == b"moov" for kind, _, _ in top):
        return [(start, end) for kind, start, end in top if kind == b"mdat"]
    meta = next(((start, end) for kind, start, end in top if kind == b"meta"), None)
    if meta is None:
        raise _Malformed("ISO media with neither movie nor meta box")
    return _heif_items(data, *meta)


# Items that hold metadata rather than picture: EXIF, XMP (a "mime" item)
# and URI-typed ones.
_HEIF_METADATA_ITEMS = {b"Exif", b"mime", b"uri "}


def _heif_items(data: mmap.mmap, start: int, end: int) -> list[Range]:
    """The extents of the picture items under the meta box payload
    [start, end), by item id."""
    children = {kind: (s, e) for kind, s, e in _boxes(data, start + 4, end)}  # FullBox
    if b"iinf" not in children or b"iloc" not in children:
        raise _Malformed("HEIF without item info or locations")
    types = _heif_item_types(data, *children[b"iinf"])
    idat = children.get(b"idat")
    ranges: list[Range] = []
    for item_id, extents in sorted(_heif_item_locations(data, *children[b"iloc"], idat).items()):
        if types.get(item_id) not in _HEIF_METADATA_ITEMS:
            ranges.extend(extents)
    return ranges


def _heif_item_types(data: mmap.mmap, start: int, end: int) -> dict[int, bytes]:
    version = data[start]
    first = start + 4 + (2 if version == 0 else 4)
    types: dict[int, bytes] = {}
    for kind, s, _ in _boxes(data, first, end):
        if kind != b"infe":
            continue
        infe_version = data[s]
        if infe_version < 2:
            raise _Malformed("HEIF item info without item types")
        if infe_version == 2:
            item_id, _, item_type = struct.unpack(">HH4s", data[s + 4:s + 12])
        else:
            item_id, _, item_type = struct.unpack(">IH4s", data[s + 4:s + 14])
        types[item_id] = item_type
    return types


def _heif_item_locations(
    data: mmap.mmap, start: int, end: int, idat: Optional[tuple[int, int]]
) -> dict[int, list[Range]]:
    version = data[start]
    off = start + 4
    sizes = data[off] << 8 | data[off + 1]
    offset_size, length_size = sizes >> 12, (sizes >> 8) & 0xF
    base_offset_size = (sizes >> 4) & 0xF
    index_size = sizes & 0xF if version in (1, 2) else 0
    off += 2

    def read(size: int) -> int:
        nonlocal off
        if off + size > end:
            raise _Malformed("item locations past their box")
        value = int.from_bytes(data[off:off + size], "big")
        off += size
        return value

    locations: dict[int, list[Range]] = {}
    for _ in range(read(2 if version < 2 else 4)):
        item_id = read(2 if version < 2 else 4)
        method = read(2) & 0xF if version in (1, 2) else 0
        read(2)  # data reference index
        base = read(base_offset_size)
        if method == 1:
            if idat is None:
                raise _Malformed("HEIF item in a missing idat box")
            base += idat[0]
        elif method != 0:
            raise _Malformed("HEIF item constructed from other items")
        extents = []
        for _ in range(read(2)):
            read(index_size)
            offset, length = read(offset_size), read(length_size)
            if length == 0:
                raise _Malformed("HEIF extent of unknown length")
            extents.append((base + offset, base + offset + length))
        locations[item_id] = extents
    return locations
