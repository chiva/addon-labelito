# Changelog

The add-on version tracks the wrapped labelito release — see the
[labelito changelog](https://github.com/chiva/labelito/blob/main/CHANGELOG.md) for the
application itself. Entries here cover the add-on wrapper.

## 0.9.0

- Wraps labelito 0.9.0: label gallery of rendered example templates, web image upload for
  label image fields, auto-numbering batches, landscape die-cut address labels (17×54 and
  29×90), column/list layout primitives, and optional HTTP Basic auth.
- Wrapper: adds the `history_keep_entries` and `history_prune_at_entries` options to bound
  the durable print-history database.
- Wrapper: disables labelito's in-app update check — this add-on is updated through the
  Supervisor, so the About dialog no longer prompts to update.

## 0.7.0

- Wraps labelito 0.7.0: optional HTTP Basic auth, a single shared API-token entry point, and
  an About dialog with built-in update checking (disabled in this add-on).

## 0.4.0

- Wraps labelito 0.4.0. No wrapper changes; tracks the upstream release.

## 0.1.3

- Initial release, wrapping labelito 0.1.3: ingress with HA-authenticated access,
  optional direct port guarded by an API token, user templates in the add-on config
  folder, durable print history, USB and network printers, Supervisor discovery.
