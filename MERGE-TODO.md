# Before merging `docker-deployment`

Temporary checklist; delete this file in the last commit before merging.

- [ ] **Pin pnpm** ([PKG-002](docs/review/2026-09-29/packaging.md#pkg-002-pnpm-version-is-not-pinned-no-packagemanager-field)).
  `ci.yml` uses `pnpm/action-setup@v4` with no `version:`. There is no root
  `package.json` with a `packageManager` field, so the setup step is
  expected to fail. Add `"packageManager": "pnpm@10.x.y"` to
  `frontend/package.json` and set `package_json_file: frontend/package.json`
  on the action. That also pins the `corepack enable pnpm` used in the Dockerfile.
- [ ] **Keep the Tailscale node keys away from the app user** ([SEC-001](docs/review/2026-09-29/security.md#sec-001-entrypoint-chowns-the-tailscale-node-state-to-the-app-user)).
  `${THALIMAGE_DATA}/tailscale` sits inside the `/data` mount, and
  `entrypoint.sh` runs `chown -R` on `/data`, so the app UID ends up owning
  `tailscaled.state`. Use sibling host dirs (`.../app` → `/data`,
  `.../tailscale` → `/var/lib/tailscale`), or limit the chown to the
  app's own paths. Update the README storage layout and `.env.example` to match.
- [ ] **Ignore coverage output.** Add `.coverage` to `.gitignore`: a
  `pytest --cov` run leaves `backend/.coverage` untracked.
- [ ] **Run CI once on the branch** (push it, or open a draft PR) and
  confirm both `ci.yml` and `docker.yml` pass.
