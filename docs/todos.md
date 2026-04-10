# Previous phases

1. ~~split pane bug~~ — fixed by keying layout render on `$page.url.pathname`

2. ~~write a readme~~ — done (README.md)

3. ~~docker~~:
   - images mounted read-only (thumbnails/DB go to /data, separate from sources)
   - multiple source dirs: mount each separately, add in Settings UI
   - PUID/PGID env vars + gosu entrypoint for file permissions

4. favicon

5. ~~settings close button~~ — done via `returnTo` query param pattern

6. when clicking on a picture, there's a back button which doesn't honor the provenance (eg: it doesn't go back to the previously selected source and in the future, collections, etc...)

7. can we persist the scroll location in the gallery so when we click an image and we come back, we are back to the same place (linked to 6.)

8. probably related to 6+7: if we click an image left/right and prev/next circulate among the full library, not the selected collection. the fix should probably not be about fixing each of this symptom but maintaining a state of selected source/collection/filter/etc so that actions refer to that selection

# Phase 2

1. ~~source switch flash~~ — fixed toolbar layout (gap instead of space-between)

2. ~~removing a source folder fails~~ — fixed: cascade-delete dependent rows (images, metadata, collection_images, elo_scores, votes). Future: source removal UX with keep/sidecar options (see Phase 2.5 in phases.md).

3. ~~mp4 thumbnail ok, no video rendering~~ — expected: Sprint 2 only added thumbnail extraction, not video playback. Video player deferred.

4. ~~no UI to enter ELO mode~~ — ELO link is on collection detail page. Bridge: added "Create Collection" button per source in Settings so ELO can be tested without manual collection creation. Will be replaced by unified collections (Phase 2.5).
