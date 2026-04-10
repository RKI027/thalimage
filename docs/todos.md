1. ~~split pane bug~~ — fixed by keying layout render on `$page.url.pathname`

2. ~~write a readme~~ — done (README.md)

3. ~~docker~~:
   - images mounted read-only (thumbnails/DB go to /data, separate from sources)
   - multiple source dirs: mount each separately, add in Settings UI
   - PUID/PGID env vars + gosu entrypoint for file permissions

4. favicon

5. ~~settings close button~~ — done via `returnTo` query param pattern

6. when clicking on a picture, there's a back button which doesn't honor the provenance (eg: it doesn't go back to the previously selected source and in the future, collections, etc...)
