# Design Decisions

Decisions the code follows, with the reasons, where neither the code nor
the in-app docs record them. The data model itself (identity by content,
collections as the universal container, global tags, per-collection ELO)
is described for users in
[`01-overview.md`](../backend/src/thalimage/docs/01-overview.md).

## Collections

- **Browsing always happens in a collection.** "All Images" is virtual:
  no database row, `id: null` in the browsing context, and no ELO.
- **Source presets are live views** of their source
  (`WHERE source_id = X`): nothing to sync on scan, one per source, not
  user-deletable.
- **Sources are scan targets.** Users manage them in Settings and browse
  them through their presets; voting, tagging and every other feature
  work on collections, never on raw sources.
- **A source removed with its data kept is hidden, not deleted** (#122):
  its images still reference it (`images.source_id` is required), so the
  row stays with `removed_at` set, and adding its folder again revives
  it. Making `source_id` nullable was rejected: a table rebuild, and
  every reader handling an image with no source. Kept images come back
  when any source holds the same picture, as identity is by content.
- **Folders are data, not browsing structure** (#29). The disk layout
  does not become sub-presets; each image gets `folder:<dir>` tags
  derived on read from its current locations (source left out), so
  they follow moved files and need no syncing. Past locations are not
  kept: they would only add noise. Searches, saved searches and the tag
  hierarchy build on these tags.
- **The browsing context lives per tab** (`lib/browsingContext.ts`, in
  session storage): clean `/image/{hash}` URLs, survives a reload, lost
  when the tab closes. A direct link to an image opens without the
  listing it came from.

## Identity

- **An image is keyed by its picture hash** (#106,
  `core/picture_hash.py`): the bytes of its picture or video data,
  without the metadata beside them, so tools writing keywords into files
  do not make new images. The containers are parsed, never decoded:
  decoders can disagree on pixels across versions. The parsers are ours,
  not ExifTool's, so a third-party release cannot shift every key; the
  fixtures were checked against ExifTool's `ImageDataHash`.
- **Keys were rewritten, not kept beside a new column.** The key stays a
  content hash everywhere, at the cost of one re-keying scan that moves
  every row, renames derived files and breaks saved image links.
  `image_locations.hash_version` records which hash keyed each location;
  raising `HASH_VERSION` re-keys on the next scan.
- **Only an unchanged file is re-keyed.** Its old key certainly named
  these bytes. A file that changed since the last scan cannot be matched
  to its old key and counts as new content.
- **A picture edited in place is a new image, offered as an edit.** A
  crop or filter changes the picture hash, and the bytes alone cannot
  tell it from an unrelated picture saved under the same name. When the
  scan replaces the picture at a path, the image that had no copy left
  and looks alike within the edit threshold (perceptual distance, 0.25
  by default) is recorded as a possible edit (`picture_edits`, #121).
  The user always decides: merging is `rekey_image`, so everything
  carries over and the old file version's metadata stays an earlier
  version, never merged into the new one. Only when the old picture has
  no copy left: a surviving copy makes the edit a derivative, a separate
  image. Whether a pair is still pending is computed on read, so a
  picture back on disk withdraws the question by itself. The edit
  threshold is its own setting: near-duplicate search (#110) asks a
  different question.
- **Near-identical pictures are found by a perceptual hash** (#121,
  `core/perceptual_hash.py`): a 64-bit DCT hash (pHash), stored per
  image and compared by the share of differing bits. It decodes the
  picture, unlike the identity hash: it only has to come close, so
  decoder differences do not matter. Measured on a library of generated
  images, it held every resize, re-encode, blur and colour change and
  most 5% crops within 0.15, and 10% crops within 0.25; 2 of 45,150
  unrelated pairs came within 0.15. dHash held crops slightly better but
  brought unrelated pairs closer; 256-bit hashes broke on crops. Our own
  code on Pillow, not `imagehash`, which pulls numpy, scipy and
  PyWavelets. Videos get none.
- **Near-duplicates are grouped around a start, not chained** (#110,
  `services/near_duplicates.py`): the first image left in the listing's
  order starts a group of every image left within the threshold of it.
  Chaining pairs drifts, so two unrelated pictures could share a group
  through a third. Overlapping groups (each image with all its near
  pictures) were wanted, but the grid shows each image once and the
  viewer steps through it, so an image takes one group: a pair split
  between two groups is the cost. The groups are a filter of the
  ordinary listing, so paging, the viewer and bulk actions work on them
  unchanged; the listing writes them to a per-connection temp table its
  queries read. An image in no group keeps its place in the sort there,
  so the viewer, left on one whose pair was just deleted, steps on to the
  groups around it.
- **All pairs are compared once, in memory, then kept up to date.** Every
  pair within 0.30 is kept, so the threshold moves without recomputing.
  The first grouped listing after a start compares all pairs, about 2 s
  at 10k images in pure Python; afterwards only images added or changed
  are compared and those gone dropped (20 ms for a deletion, 70 ms for
  100 new images). Recomputing everything on each change stalled the
  viewer and the grid after every deletion. The pairs are also written to
  `cache/near-duplicates.json` after each change (1.4 MB and 25 ms at
  10k) and read at startup, so a restart only compares what changed
  meanwhile. The file holds the hashes it was computed from, so a stale
  one costs comparisons, never wrong groups. It sits in the cache, not
  the database: it is derived, and would only bloat the backups. A VP-tree was measured at 4x slower: 64-bit
  Hamming distance takes few values and prunes little within 10 bits,
  and each node visit is a Python call. Revisit (a multi-index on hash
  blocks, or storing pairs at scan) if the library grows well past 10k.
- **Merging replays ELO** rather than combining scores: `elo_scores`
  holds running scores, so the merged image's votes are replayed in order
  (`replay_scores`), and only in the collections they touched, so a
  change of formula does not shift scores elsewhere.

## Renaming files

- **Files are renamed to their picture hash** (#14), not a GUID: the
  name stays right when tools write metadata into the file, and copies
  of one picture get the same name. Only the name changes, never the
  folder, so folder tags are unaffected.
- **Per source, not by guessing from names.** Whether a name is worth
  keeping (one's own generations, game screenshots) depends on where the
  file comes from, so a writable source opts in and each scan renames its
  files; the viewer's Rename handles strays. A name heuristic was
  rejected: bad names (user-chosen, NSFW) cannot be told from good ones.
- **The first name seen is kept per file version**
  (`file_metadata.original_name`), recorded at every scan and never
  replaced, so it survives renames by hand too. It is not location
  history (#29 keeps none): it is one name per file version.
- **A redundant copy is deleted, only within its folder.** When the
  folder already holds the image under its hash name, the copy goes;
  each file's metadata stays in `file_metadata`. Copies in other folders
  are renamed in place and kept. A sidecar whose new name is taken is
  deleted only when identical, else left as an orphan, so no sidecar
  content is lost.

## Deployment

- **Tailnet only.** The app runs on a Tailscale sidecar's network
  namespace and publishes nothing to the host. Traefik was considered and
  not used: it would need a tailnet-bound entrypoint on the shared homelab
  stack, a DNS record, and Tailscale on the Traefik host. Revisit only if
  the homelab standardises on one proxy. The tailnet is the whole access
  boundary: there is no authentication in the app (#98).
- **Creation dates.** Python reports no birth time on Linux, so files
  first scanned in the container have no `file_created`; sorting and the
  viewer fall back to `file_modified`. On the first deployed library the
  two differed by under 5 s for all but 3 of 1,387 files, and almost none
  embed a date. `statx` was rejected: copying files to the NAS gave them
  new birth times while their mtimes survived. Rescans keep the earliest
  known date. Revisit for a library whose files are edited after
  creation.

The history behind these, phase by phase, is in the archived
[roadmap](archive/roadmap.md).
