# Image delivery

Three different sizes of the same image are served, and which one you
get depends on where you are looking.

| Where | What is sent |
|---|---|
| Gallery grid | Thumbnail — WebP, 400px long edge |
| Viewer, slideshow, voting | Preview — WebP, capped at your screen size |
| Video playback | The original file, streamed, or a copy iOS can play |

## Why previews exist

Originals in a typical library average several megabytes and can reach
tens of megabytes — one 3328x6144 PNG measured here is 36.6 MB. A phone
screen needs roughly 1200 pixels on the long edge, so sending the
original means sending a hundred times more data than the screen can
show. Over wifi, that is the difference between an image appearing
instantly and waiting several seconds for it.

A preview of that 36.6 MB PNG is 73 KB.

## How previews are made

Previews come in three sizes — 1280, 1920 and 2560 pixels on the long
edge. The browser asks for the size it needs, based on the window and
the device pixel ratio, and the server rounds up to the nearest of the
three; a screen that needs more than 2560 pixels gets the 2560 preview.
Sources smaller than the bucket are never upscaled.

Generation happens on first request, not during a scan: resizing a large
PNG takes roughly half a second, paid once, after which the result is
cached on disk under `cache/previews/` and served directly. Scans stay
fast and disk fills only with images actually looked at.

Because every URL is addressed by content hash, it can never mean
something different later, so responses are cached by the browser for a
year without revalidating.

## Video

Video is served as the original file, with range requests supported —
playback and seeking start without downloading the whole file first.
There is no reduced preview encode, so a large video is still a large
video.

iPhones and iPads play only some formats, in every browser and in the
home-screen app alike: H.264, HEVC and AV1 video, with AAC or MP3 audio,
in an MP4 or MOV file. For any other video (VP9 or WebM files, MKV
files, Opus audio), a scan writes an MP4 copy under `cache/videos/`, and
the viewer plays that copy everywhere. The copy reuses what already
plays and converts the rest: a file that only needs a different
container takes seconds, while re-encoding VP9 to H.264 takes a few times
the video's length. Your original file is never changed. The copy is
deleted with its image or its source.
