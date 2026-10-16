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
- **The browsing context lives per tab** (`lib/browsingContext.ts`, in
  session storage): clean `/image/{hash}` URLs, survives a reload, lost
  when the tab closes. A direct link to an image opens without the
  listing it came from.

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
