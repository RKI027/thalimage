# Phase 1 / MCP

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

9. ~~source switch flash~~ — fixed toolbar layout (gap instead of space-between)

10. ~~removing a source folder fails~~ — fixed: cascade-delete dependent rows (images, metadata, collection_images, elo_scores, votes). Future: source removal UX with keep/sidecar options (see Phase 2.5 in phases.md).

11. ~~mp4 thumbnail ok, no video rendering~~ — expected: Sprint 2 only added thumbnail extraction, not video playback. Video player deferred.

12. ~~no UI to enter ELO mode~~ — ELO link is on collection detail page. Bridge: added "Create Collection" button per source in Settings so ELO can be tested without manual collection creation. Will be replaced by unified collections (Phase 2.5).

13. ~~on create collection, the sidebar doesn't register the new collection~~ — fixed via shared stores

14. ~~rapid GET /api/v1/collections requests~~ — fixed: $effect reactivity loop (untrack async calls) + route-group keying in layout

15. ~~toolbar flash on collection switch~~ — fixed: toolbar always rendered, route-group key avoids remount between sibling routes

16. remove a source doesn't remove the collection. creating a collection from a non-scanned source then scanning the source doesn't update the collection (can still create a new collection). this doesn't need to be fixed as it's part of phase 2.5.
