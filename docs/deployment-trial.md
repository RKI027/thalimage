# First Deployment — Findings to Fold into the Docs

The first real run of the Docker stack (Portainer on a host with the
images and the data directory on an NFS share). Each entry is either
fixed on the branch or still to be written into README / CLAUDE.md /
the roadmap, which still say the deployment has never been run. Fold
this file into those once the open items are settled, then delete it.

## Fixed in code

- **`serve.json` mounted as an empty directory.** A stack pasted into
  Portainer has no `./serve.json` beside it; Docker creates the missing
  source as a directory and `tailscale serve` never starts (log:
  `read /config/serve.json: is a directory`). Now mounted from
  `THALIMAGE_DATA/serve.json`.
- **Sidecar re-logging in on every start.** `TS_AUTH_ONCE=true`.
- **Stale page after an upgrade.** `index.html` had no `Cache-Control`,
  so the browser kept the previous build's bundle (the version line in
  Settings showed two different commits). Now `no-cache`, with hashed
  assets immutable.
- **Every page loaded twice per navigation**, and an NSFW collection
  could show empty until a reload (the first listing raced the
  settings). Both fixed in the frontend.

## To document

- **Tailscale prerequisites.** The tag in `TS_TAG` must exist in
  `tagOwners` *with an owner*: without one the first join can succeed
  and a later restart fails with `requested tags [...] are invalid or
  not permitted`.
- **Auth key.** Settings → Keys → Generate auth key (not "Add app",
  which is an App Connector): not reusable, not ephemeral, tagged with
  `TS_TAG`, pre-approved if device approval is on.
- **`THALIMAGE_ALLOWED_HOSTS`** is a JSON list (`["host.tailnet.ts.net"]`);
  anything else crashes startup with `error parsing value for field
  "allowed_hosts"`. A scheme or a short name gives "Invalid host header".
  Prefer the exact MagicDNS name once known.
- **Open the `https://` URL.** Only 443 is served; a bare name may try
  port 80 and fail with "can't connect".
- **Data layout.** `app/` (database, caches) is a sibling of
  `tailscale/`, so the app's startup chown never reaches the node keys.
  A stack built from the older compose file mounted all of
  `THALIMAGE_DATA` and has to be moved over (and `tailscale/` handed back
  to root).
- **Moving an existing database in.** Checkpoint the WAL before copying;
  rewrite `sources.path` to container paths (images are stored relative
  to their source); copy `cache/` along. If the copy changed file
  mtimes, the next scan reprocesses everything and records the copy
  dates — restore the files' mtimes first.
- **Testing a branch.** Run the publish workflow by hand on the branch;
  it moves `:dev`. A deployment on `THALIMAGE_TAG=dev` picks it up on
  redeploy with "re-pull image".

## Open

- **Requests taking 10–35 s, server-side.** The data directory (SQLite
  in WAL mode) is on NFS, which SQLite does not support for WAL. Measure
  again with the double loading fixed; if it persists, move
  `THALIMAGE_DATA/app` to local disk and compare.
- **Creation dates** are not read inside the container (see the roadmap's
  Unsorted list).
