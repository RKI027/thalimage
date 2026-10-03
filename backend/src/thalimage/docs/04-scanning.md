# Scanning

A scan walks a source folder, finds images and videos, and records what
it finds. Re-scanning is safe and cheap: a file whose path, size and
modification time are unchanged since the last scan is skipped without
being read — unless metadata extraction has improved since it was read,
in which case it is read once more to pick that up.

## What happens to each new or changed file

1. **Hashing.** The file is read and hashed with SHA-256. This hash is
   the image's identity everywhere in the app.
2. **Metadata extraction.** Dimensions and format come from the file
   header. For AI-generated images, the generation parameters embedded
   by tools such as Automatic1111 and ComfyUI are parsed out where
   present — prompt, model, sampler, seed and so on.
3. **Thumbnail generation.** A 400px WebP is written to `cache/thumbs/`.
   For videos, a frame is pulled with ffmpeg at 10% into the runtime,
   which usually avoids a black opening frame.
4. **Recording.** The image and where it was found are written to the
   database, a few dozen files at a time, so the rest of the app stays
   responsive during a long scan.

A file that cannot be read or decoded is counted as an error and the
scan carries on with the next one; what was indexed for it before stays
as it was.

Videos need ffmpeg and ffprobe on the system path. Without them, video
files are skipped and counted as errors: they do not appear until a scan
runs with ffmpeg available.

## Source presets

Each source folder has a matching preset collection. It is a live view
of the images in that source rather than a stored list, so it is always
current and nothing needs syncing; the scan only makes sure it exists.

## The same file in several places

Two identical files are one image, wherever they are: in two folders of
one source, or in two sources. The image lists under every source it
lies in and keeps one set of tags, scores and collection memberships.
It is opened from one of its copies; if that copy disappears, the app
switches to another. The image only counts as deleted once no copy is
left anywhere.

## When a source cannot be read

If the source folder is missing, is not a folder, or cannot be read —
an unplugged drive, a share that did not mount — the scan stops with an
error and changes nothing. The same goes for a folder that turns out
empty although images were indexed from it, which is what an unmounted
share's leftover mount point looks like. Rescan once the folder is back.

If only a subfolder cannot be read, the scan indexes the rest and leaves
the images under that subfolder as they were.

## Archived and deleted

**Archived** images stay in the database with everything attached —
tags, scores, collection memberships — but drop out of galleries and out
of voting. It is a way of setting something aside without losing it.

**Deleted** marks an image whose file is no longer on disk anywhere. The
row is kept so that tags and scores survive if the file comes back.

Neither flag touches your original files. Thalimage never writes to or
removes anything in a source folder.

## Removing a source

Deleting a source removes its preset collection and every image found
only in that source, together with its metadata, scores, tags and
collection memberships, with no prompt and no undo. Images that also lie
in another source are kept, with everything attached. A more careful
flow, offering to keep the database entries or to write them out to
sidecar files first, is designed but not yet built.
