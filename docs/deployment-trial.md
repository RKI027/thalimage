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
- **Requests taking 10–35 s: the database on NFS.** Still there with the
  double loading fixed (four concurrent requests stalled 12 s together).
  Measured in the container, 4 threads × 25 rounds of the app's
  connect-and-query: on NFS median 9–15 ms but max 3.1 s and 35.7 s
  (p90 30 s on the second run); on local disk max 22 ms. SQLite does not
  support WAL on network filesystems. The database now has its own
  mount, `THALIMAGE_DB_DIR`, on the host's local disk; caches stay on
  the share. Redeployed that way, no stall could be triggered.
- **Creation dates erased by rescans.** Every re-indexed file came back
  with no birth time (Linux reports none) and the scan wrote that over
  the macOS-recorded date: all 958 images lost theirs. Rescans now keep
  the earliest known date; the lost ones were restored from the
  pre-deployment database by content hash. New files fall back to the
  mtime, which matches the creation time for this library (see the
  roadmap's Unsorted list).
- **Backups for a database off the NAS.** A daily in-app backup (time
  and copies kept set in Settings) writes into `db_backups/` on the
  share, so the NAS still holds a recent copy.

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
- **Data layout.** `app/` (caches, database backups) is a sibling of
  `tailscale/`, so the app's startup chown never reaches the node keys.
  A stack built from the older compose file mounted all of
  `THALIMAGE_DATA` and has to be moved over (and `tailscale/` handed back
  to root).
- **Moving an existing database in.** Checkpoint the WAL before copying;
  rewrite `sources.path` to container paths (images are stored relative
  to their source); copy `cache/` along. If the copy changed file
  mtimes, the next scan reprocesses everything and records the copy
  dates — restore the files' mtimes first.
- **`THALIMAGE_DB_DIR` and `TZ`.** The database folder is required and
  must be local disk; `TZ` sets the zone the backup time is read in.
  Moving an existing database there: stop the stack, move
  `app/thalimage.db*` into `THALIMAGE_DB_DIR`, redeploy.
- **Restoring a backup.** Stop the stack, copy a
  `db_backups/thalimage-*.db` over `THALIMAGE_DB_DIR/thalimage.db`,
  delete any `thalimage.db-wal`/`-shm` beside it, start.
- **Testing a branch.** Run the publish workflow by hand on the branch;
  it moves `:dev`. A deployment on `THALIMAGE_TAG=dev` picks it up on
  redeploy with "re-pull image".
