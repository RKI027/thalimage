# Scanning

A scan walks a source folder, finds images and videos, and records what
it finds. Re-scanning is safe and cheap: a file already known by its
hash is skipped.

## What happens to each file

1. **Hashing.** The file is read and hashed with SHA-256. This hash is
   the image's identity everywhere in the app. Two identical files in
   different folders are one image.
2. **Metadata extraction.** Dimensions and format come from the file
   header. For AI-generated images, the generation parameters embedded
   by tools such as Automatic1111 and ComfyUI are parsed out where
   present — prompt, model, sampler, seed and so on.
3. **Thumbnail generation.** A 400px WebP is written to `cache/thumbs/`.
   For videos, a frame is pulled with ffmpeg at 10% into the runtime,
   which usually avoids a black opening frame.
4. **Preset sync.** Each source folder has a matching preset collection,
   kept up to date as the scan runs.

Videos require ffmpeg and ffprobe on the system path. Without them,
video files are still catalogued but get no thumbnail.

## Archived and deleted

**Archived** images stay in the database with everything attached —
tags, scores, collection memberships — but drop out of galleries and out
of voting. It is a way of setting something aside without losing it.

**Deleted** marks an image whose file is no longer on disk. The row is
kept so that tags and scores survive if the file comes back.

Neither flag touches your original files. Thalimage never writes to or
removes anything in a source folder.

## Removing a source

Deleting a source currently removes everything associated with it —
image rows, metadata, scores, tags and collection memberships — with no
prompt and no undo. A more careful flow, offering to keep the database
entries or to write them out to sidecar files first, is designed but not
yet built.
