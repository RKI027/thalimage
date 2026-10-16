#!/usr/bin/env bash
# Regenerates the picture-hash fixtures: for each format, a small picture
# (NAME.EXT), the same file with metadata written into it by ExifTool
# (NAME-tagged.EXT), and a different picture (NAME-other.EXT).
# Needs ImageMagick, ffmpeg and ExifTool; the tests only read the output.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
rm -f -- *.png *.jpg *.webp *.tiff *.avif *.mp4 *.mov

picture() { magick -size 16x16 "plasma:fractal" -seed "$1" "${@:2}"; }
for ext in png webp tiff avif; do
    picture 1 "picture.$ext"
    picture 2 "picture-other.$ext"
done
picture 1 picture.jpg
picture 2 picture-other.jpg
picture 1 -interlace JPEG progressive.jpg
picture 2 -interlace JPEG progressive-other.jpg

clip() { ffmpeg -loglevel error -f lavfi -i "testsrc=size=16x16:rate=5" -t 1 -vf "hue=h=$1" "$2"; }
for ext in mp4 mov; do
    clip 0 "clip.$ext"
    clip 90 "clip-other.$ext"
done

for f in picture.png picture.webp picture.tiff picture.avif picture.jpg progressive.jpg clip.mp4 clip.mov; do
    tagged="${f%.*}-tagged.${f##*.}"
    cp "$f" "$tagged"
    exiftool -q -overwrite_original -XMP-dc:Subject=beach -Rating=5 \
        -Comment="a lighthouse" "$tagged"
done
