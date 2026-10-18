# Selecting images

The gallery, a source and a collection let you select several images and
act on them at once.

## Selecting

**Select** in the toolbar (in the menu on a phone) starts selecting.
While selecting, clicking an image selects or unselects it instead of
opening it, and Shift-click selects every image between the last one
clicked and this one, in the order the grid shows them. On a computer,
Ctrl-click (Cmd-click on a Mac) starts selecting with that image
straight away.

**Done**, or Escape, stops selecting and forgets the selection. Changing
the sort or the filters forgets it too, as the grid then shows another
listing.

## Acting on the selection

The bar that appears while selecting offers:

- **Archive**, or **Unarchive** when the Archived filter lists archived
  images. Archived images leave browsing, as *Scanning* describes.
- **Tag** and **Untag**: pick a tag, or type a new name to create one.
  Untagging leaves the images that do not carry the tag as they are.
- **Add to collection**: pick one of your own collections. Images
  already in it stay as they are.
- **Remove from collection**, in a collection you curated: the images
  leave this collection only; their tags and scores elsewhere are kept.
- **Delete from disk…**: every copy of every selected image, with their
  sidecars, after a confirmation that lists each file. It follows the
  rules of deleting one image, described in *Scanning*: if any image
  may not be deleted, none is. A file that then fails to be removed is
  named in the confirmation, and its image stays.

Each action applies to every selected image or, if it fails, to none.
Afterwards the selection is forgotten and the grid reloads, since
archived or removed images leave it.

## Reviewing a group

A review goes through a group of images, one against another, to decide
what to keep. Open one with **Review** in the selection bar (two images
or more selected), or with **Review group** (**R**) in the viewer, when
it was opened from a grid filtered to near-duplicates: the review then
takes the group of the image shown, and can go on to the next group.

One image is the **reference**: the one with the most pixels, then the
largest file. The others are the **current** image in turn. A strip
above shows the whole group, each image marked as the reference or with
its flag; clicking one shows it.

### Comparing

Three views show the reference and the current image, switched with the
buttons or **M**:

- **Side by side**: the two next to each other (one above the other on a
  phone).
- **Toggle**: one at a time, filling the view. **T** switches to the
  other.
- **Overlay**: the current image over the reference, both fitted to the
  same frame. **Blend** mixes them, a slider setting how much of the
  current image shows through; **wipe** splits them at a divider, the
  reference on its left: press or drag anywhere on the picture to move
  it. **O** switches between blend and wipe. Videos cannot be overlaid.

In the toggle and overlay views, holding **Space** shows only the
reference until you let go, to flash between the two.

Under the pictures, their dimensions, file size, format, dates, files
and tags are listed side by side, each line that differs highlighted.
The current image's tags can be edited below them; tags change at once,
unlike flags.

### Flagging

- **←** / **→**: the previous or next image after the reference.
- **F**: make the current image the reference.
- **A**, **G**, **D**: flag the current image to **archive**, to
  **merge** into the reference, or to **delete** from disk. The same key
  again clears the flag. With **Shift**, they flag the reference instead
  (archive or delete only: it cannot merge into itself).
- **U**: undo the last flag.

### Leaving

Flags change nothing until you leave. **Escape** (or **Done**) goes back
to the grid, and **Next group** (**N**) to the next near-duplicate
group. With images flagged, either first lists them by action, each with
the files it would remove, and offers to **Apply** them, **Discard**
them, or **Keep reviewing**; applying or discarding then goes where you
were going. Images left unflagged stay as they are.

Merging an image into the reference deletes its files from disk and
gives the reference its tags, collections, votes and scores, and its
file versions' metadata as earlier versions; votes between the two are
dropped. Like deleting, it needs every copy of the image in a writable
source, and if one file cannot be removed, that image is not merged.
The reference cannot be deleted while other images merge into it.
