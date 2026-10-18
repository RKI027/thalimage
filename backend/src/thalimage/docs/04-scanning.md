# Scanning

A scan walks a source folder, finds images and videos, and records what
it finds. Re-scanning is safe and cheap: a file whose path, size and
modification time are unchanged since the last scan is skipped without
being read — unless metadata extraction or the way images are
identified has improved since it was read, in which case it is read
once more to pick that up.

Files and folders that operating systems and NAS software leave behind
are never looked at: `.DS_Store` and `._*` files (macOS), `Thumbs.db` and
`desktop.ini` (Windows), `*@SynoEAStream` files and `@eaDir` folders
(Synology), and the `#recycle`, `.Trash*` and `$RECYCLE.BIN` trash
folders. Images inside them, such as Synology's own thumbnails, are not
indexed.

## What happens to each new or changed file

1. **Hashing.** The file is read and its picture or video data hashed
   with SHA-256, leaving out the metadata stored beside it (EXIF, XMP,
   comments, keywords). This hash is the image's identity everywhere in
   the app, so a tool writing keywords or a rating into a file leaves it
   the same image. JPEG, PNG, WebP, TIFF, AVIF/HEIC, MP4 and MOV files
   are read this way; other formats (GIF, BMP, MKV, WebM, AVI) are
   hashed whole, so for them a metadata edit makes a new image.
2. **Metadata extraction.** Dimensions and format come from the file
   header. For AI-generated images, the generation parameters embedded
   by tools such as Automatic1111 and ComfyUI are parsed out where
   present — prompt, model, sampler, seed and so on.
   Keywords and star ratings that photo tools (Windows Explorer,
   digiKam, Lightroom…) wrote into the file become tags: each keyword a
   tag of that name, joining an existing tag whatever its case, and a
   rating a `rating:N` tag. Removing such a tag in Thalimage is final:
   reading the file again does not bring it back.
3. **Perceptual hash.** Still images also get a 64-bit fingerprint of
   what the picture looks like, read from its pixels. Unlike the hash
   above, it barely changes when the picture is resized, re-encoded,
   slightly cropped or its colours adjusted, so it can tell that two
   different files show nearly the same picture. Videos get none.
   Images scanned before this existed are read once more to get one.
4. **Thumbnail generation.** A 400px WebP is written to `cache/thumbs/`.
   For videos, a frame is pulled with ffmpeg at 10% into the runtime,
   which usually avoids a black opening frame.
5. **Recording.** The image and where it was found are written to the
   database, a few dozen files at a time, so the rest of the app stays
   responsive during a long scan.
6. **Playable videos.** Once everything is recorded, each video not seen
   before is checked, and those iOS cannot play get an MP4 copy (see
   Image delivery). The scan shows this as "Checking videos", then
   "Making videos playable on iOS"; the images are already browsable
   while it runs. The first scan after an upgrade checks every video
   once, which takes a while on a large library.

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
It is named after the source's label, or its folder when it has none;
use the source's **Relabel** in Settings to rename the preset.

## The same picture in several places

Files holding the same picture are one image, wherever they are: in two
folders of one source, or in two sources, and even when the metadata in
them differs. The image lists under every source it
lies in and keeps one set of tags, scores and collection memberships.
It is opened from one of its copies; if that copy disappears, the app
switches to another. The image only counts as deleted once no copy is
left anywhere.

Each file keeps its own metadata: the prompt, parameters, EXIF and PNG
text read from it. The image shows the metadata of the copy it is opened
from, and its information panel notes when other files of the same
image carry a different prompt, negative prompt or generation tool. A file's metadata stays with the
image after the file is deleted or disappears, so removing a copy never
loses it.

## When the way images are identified changes

Images used to be identified by a hash of the whole file, metadata
included. The first scan after upgrading reads every file once more, as
it does when metadata extraction improves, and gives each image its new
identity:

- An image whose file is unchanged since the last scan keeps its tags,
  votes, scores and collection memberships. Its thumbnail, previews and
  playable video copy follow it.
- Images that turn out to hold the same picture become one. Their tags,
  collection memberships and each file's metadata combine and their
  votes move to it; a vote between the two is dropped. The scores of the collections concerned
  are recomputed from their votes, in the order they were cast.
- A file that changed since the last scan counts as new content, as it
  always has.

Links to an image saved before the upgrade no longer open it.

## Folder tags

The folder a file sits in, within its source, gives the image a
`folder:` tag: `portraits/2024/a.png` is tagged `folder:portraits/2024`.
An image with copies in several folders has one such tag per folder; a
file directly in the source folder has none. The source itself is not
part of the tag.

Folder tags follow the files: they always reflect where the copies are
now, so moving a file and scanning again changes them. They show in the
image's information panel but cannot be added or removed by hand, and no
other tag can be named `folder:…`.

Filtering on a folder tag also matches its sub-folders: `folder:portraits`
finds the images in `portraits`, `portraits/2024` and so on.

## Why a source has fewer images than files

Each source in Settings sets the files indexed in it against the images
its preset shows ("1,390 files → 954 images"), followed by whatever
explains the difference, each opening onto the files concerned:

- **Duplicate files**: copies of the same picture as another file in
  the source. They are one image. A copy marked *different metadata*
  holds the same picture as the group's first file but other metadata
  (an edited prompt, a stripped EXIF block); the others are identical
  files. In a writable source (see below) you
  can tick copies and delete them from disk, after a confirmation that
  lists every file with its sidecars (see below). Each image keeps at
  least one copy, and a file that changed since the last scan is refused
  until you rescan. A deleted copy's metadata stays with the image, and the confirmation
  names the copies whose metadata differs from every copy kept. When
  a deleted copy's sidecar differs from every sidecar of the copies
  kept, the confirmation warns that its content will be lost.
- **Files not indexed**: files the last scan could not read or decode,
  and subfolders it could not list, with the reason. Files it could not
  rename to their picture hash are listed here too, although they are
  indexed. A new file that
  fails is not counted at all; one indexed before keeps its earlier
  entry. Every scan replaces this list.
- **Archived images**: indexed, but left out of browsing.

Below those, **Orphan files** lists the files in the source that are
neither images nor videos and that no image or video in their folder is
named after (see sidecars below): the sidecar of a file that was deleted
or renamed, but also any other file, such as a `README`.
They are not indexed and do not count among the files.

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
A collection's image count leaves them out too; when it holds archived
images, an archive icon next to the count says how many.

To find them again, set the **Archived** filter to **Only**, in the
gallery, a source or a collection: the grid then lists the archived
images, the viewer walks them, and each can be unarchived from the
viewer. Voting never draws archived images, whatever that filter says.

**Deleted** marks an image whose file is no longer on disk anywhere. The
row is kept so that tags and scores survive if the file comes back.

Neither flag touches your original files.

## Sidecar files

A sidecar is a file next to an image or video, named after it, that
Thalimage does not index: `img.txt` or `img.png.json` beside `img.png`.
Generation tools write them, such as Forge's parameters `.txt` or a
ComfyUI workflow `.json`. Deleting a file deletes its sidecars too,
unless another image or video in the same folder is named the same
(`img.jpg` beside `img.png` and `img.txt`); the sidecar then stays
until the last of them is deleted.

Each scan records every sidecar with a digest of its content, so it
notices a sidecar added, changed or removed even when the image beside
it is unchanged. The scan's completion message counts them. A sidecar
whose size and modification time are unchanged is not read again.

The full information panel in the viewer lists an image's sidecars under
**Sidecars**, collapsed until you open it, with the text of each. Copies
whose sidecars say the same thing are shown once. Binary files and files
over 256 KiB are listed by name and size only.

## Deleting an image

**Delete…** in the image viewer removes every copy of the image from
disk, in every source, with their sidecars, after a confirmation that
lists each file. All those sources must be writable; if one is not, the
confirmation names it and offers no way to go ahead. A copy that changed since the last
scan refuses the whole delete until you rescan. **Delete from disk…**
on a selection of images (see *Selecting images*) does the same for
each of them at once: one source that is not writable, or one changed
copy, refuses the delete of them all.

The image is then marked deleted, as above: it leaves the gallery, but
its tags, scores, votes and collection memberships are kept, and come
back if a scan finds the same file again. If some copy could not be
removed, the image stays, and the confirmation says which and why.

## Renaming files to their picture hash

A file can be renamed to the image's picture hash (see Hashing above),
keeping its extension: `cat (1).png` becomes `3f9a…c2.png`, with the full
64-character hash. Only the name changes; the file stays in its folder,
so its folder tags are unaffected. Its sidecars are renamed with it:
`cat (1).txt` becomes `3f9a…c2.txt`, `cat (1).png.json` becomes
`3f9a…c2.png.json`. A sidecar that another image or video in the folder
is also named after stays where it is.

Each scan records the name it first sees for every file version, and
never replaces it, so the original name is kept after a rename, and also
after you rename the file yourself once it has been scanned. The
information panel shows it as **Original name** when it differs from the
current one.

When the folder already holds the same picture under its hash name, the
copy being renamed is redundant and is deleted instead, whether it is an
identical file or holds other metadata: each file's metadata stays with
the image (see above). Its sidecars move to the hash name when that is
free, are deleted when the kept copy has a sidecar of the same name and
content, and otherwise stay where they are, as orphans.

There are two ways to rename:

- **Rename…** in the image viewer renames every copy of the image, in
  every source, after a confirmation that lists them. As with deleting,
  every source holding a copy must be writable, and a copy that changed
  since the last scan, or whose hash name is taken by another file,
  refuses the whole rename before anything is touched.
- **Rename files to their picture hash**, a setting of each writable
  source in Settings, renames every file of the source at the end of
  each scan, starting with the scan that follows. A file that cannot be
  renamed is listed under **Files not indexed** with the reason; the
  rest are renamed. Making the source read-only turns the setting off.

Every rename is recorded with the other changes Thalimage makes to files
(see below).

## Read-only and writable sources

A source is read-only unless you mark it writable, when adding it or
later in Settings. Thalimage never writes to, renames or removes
anything in a read-only source. Marking a source writable first checks
that its folder accepts writes (by creating and removing a temporary
file), and is refused if it does not, e.g. when it is mounted read-only.
Every change Thalimage then makes to files is recorded in the database
(`file_changes`: what, where, when, and whether it worked), and the
record is kept even after the source is removed.

## Removing a source

**Remove** in Settings asks what to do with the images found only in
that source, and says how many there are. Removing never touches the
files on disk, and images that also lie in another source are kept
either way, with everything attached. The source's preset collection
goes in both cases.

- **Keep their data** marks those images deleted (see
  *Archived and deleted* above): they leave every
  gallery, collection and vote, but their tags, scores, collection
  memberships and metadata stay in the database. Once a scan finds the
  same pictures again, in the same folder added back or in any other
  source, they return with all of it.
- **Remove their data** deletes those images from the database with
  their metadata, scores, tags and collection memberships. There is no
  undo; a later scan of the same files indexes them as new images.

Writing that data to sidecar files before removing a source is not yet
built.
