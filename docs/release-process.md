# Release process

The add-on is a thin wrapper around the upstream `ghcr.io/chiva/labelito` image: a Dockerfile that
adds an entrypoint translating the add-on's `options.json` into labelito's environment, plus the
Home Assistant manifest. The wrapper image is published as `ghcr.io/chiva/labelito-addon`.

## Version = wrapped labelito version

The Supervisor pulls the tag matching `config.yaml`'s `version`, so three things must stay in
lockstep on every labelito release:

1. `labelito/build.yaml` → `build_from.*` (the per-arch base image the builder injects)
2. `labelito/Dockerfile` → `ARG BUILD_FROM` default (keeps a plain `docker build` working)
3. `labelito/config.yaml` → `version` (the tag the Supervisor pulls)

**Renovate** watches `ghcr.io/chiva/labelito` and opens a single grouped PR bumping all three when
upstream publishes a release (see [`renovate.json`](../renovate.json)). The `prepare` job in
[`build-app.yaml`](../.github/workflows/build-app.yaml) verifies the three agree and fails before any
image is pushed — every build/publish job depends on it — so a partial bump can never publish a
wrapper tag that points at the wrong upstream image.

## CI/CD

- **[`lint.yaml`](../.github/workflows/lint.yaml)** — add-on linter, shellcheck, hadolint, yamllint
  on every PR/push and nightly.
- **[`builder.yaml`](../.github/workflows/builder.yaml)** + **[`build-app.yaml`](../.github/workflows/build-app.yaml)**
  — build-only on PRs; on merge to `main`, build the multi-arch image and publish
  `ghcr.io/chiva/labelito-addon:<version>` + `:latest`.
- **[`pr-title.yml`](../.github/workflows/pr-title.yml)** — enforces a Conventional Commit PR title.

So the normal release flow is: Renovate PR bumps the version → merge → the multi-arch image
publishes automatically → the Supervisor offers the update.

### Manual recovery

If a publish run fails partway, hits a transient GHCR error, or the current tag otherwise needs
re-pushing, trigger **builder.yaml** manually (**Actions → Builder → Run workflow**). A manual run
rebuilds and republishes every add-on at its current `config.yaml` version, bypassing the
changed-file filter; re-pushing the same tags is idempotent, so no version churn is needed.
