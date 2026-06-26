# Phase 1 / MCP

1. ~~split pane bug~~ — fixed by keying layout render on `$page.url.pathname`

2. ~~write a readme~~ — done (README.md)

3. ~~docker~~:
   - images mounted read-only (thumbnails/DB go to /data, separate from sources)
   - multiple source dirs: mount each separately, add in Settings UI
   - PUID/PGID env vars + gosu entrypoint for file permissions

4. favicon

5. ~~settings close button~~ — done via `returnTo` query param pattern

6. ~~back button doesn't honor provenance~~ — fixed: browsing context store tracks origin, back returns to correct grid with label

7. ~~scroll position lost on back navigation~~ — fixed: scroll position saved to sessionStorage, restored on return

8. ~~prev/next circulates full library instead of current collection~~ — fixed: browsing context scopes prev/next to current collection

# Phase 2

9. ~~source switch flash~~ — fixed toolbar layout (gap instead of space-between)

10. ~~removing a source folder fails~~ — fixed: cascade-delete dependent rows (images, metadata, collection_images, elo_scores, votes). Future: source removal UX with keep/sidecar options (see Phase 2.5 in phases.md).

11. ~~mp4 thumbnail ok, no video rendering~~ — expected: Sprint 2 only added thumbnail extraction, not video playback. Video player deferred.

12. ~~no UI to enter ELO mode~~ — ELO link is on collection detail page. Bridge: added "Create Collection" button per source in Settings so ELO can be tested without manual collection creation. Will be replaced by unified collections (Phase 2.5).

13. ~~on create collection, the sidebar doesn't register the new collection~~ — fixed via shared stores

14. ~~rapid GET /api/v1/collections requests~~ — fixed: $effect reactivity loop (untrack async calls) + route-group keying in layout

15. ~~toolbar flash on collection switch~~ — fixed: toolbar always rendered, route-group key avoids remount between sibling routes

16. ~~source/collection sync issues~~ — fixed: source presets auto-created/synced in Phase 2.5

# Phase 2.5

17. ~~navigating to the /collections isn't easy~~ — fixed: gear icon on sidebar Collections header links to /collections

18. ~~from /collections, deleting or creating one doesn't update the sidebar~~ — fixed: collectionsStore.refresh() after create/delete
