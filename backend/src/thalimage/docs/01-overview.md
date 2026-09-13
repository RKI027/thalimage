# Overview

Thalimage is a self-hosted browser for AI-generated images. It scans
folders you point it at, extracts what metadata it can, and keeps
everything in a local SQLite database. Nothing leaves the machine.

These pages document behaviour that is real but not visible from the
interface — how images are picked for voting, which size of a file gets
sent to your screen, what a scan actually does. They exist so that the
answers live somewhere other than the source code.

## Core ideas

**Images are identified by content, not by path.** Every file is hashed
with SHA-256, and that hash is its identity. Move a file, rename it, or
keep the same image in two folders, and it is still one image with one
set of tags, votes and scores.

**Collections are the universal container.** Browsing always happens
inside one: a preset that tracks a source folder, a collection you
curated by hand, or the virtual "All Images". Features like voting
operate on collections, never on raw folders.

**Tags are global, scores are local.** A tag applied to an image applies
everywhere. An ELO score belongs to one collection, so the same image
can rank near the top of one set and the middle of another.
