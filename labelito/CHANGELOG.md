# Changelog

The add-on version tracks the wrapped labelito release — see the
[labelito changelog](https://github.com/chiva/labelito/blob/main/CHANGELOG.md) for the
application itself. Entries here cover the add-on wrapper.

## 0.17.0

- Wraps labelito 0.17.0. Notable application features accumulated since 0.10.0: a visual
  drag-and-drop label builder in the Studio (0.15.0), draft printing from the Studio (0.13.0),
  and a Model Context Protocol (MCP) server for AI clients (0.17.0).
- Wrapper: adds the `mcp_enabled` option (off by default) to expose labelito's MCP server at
  `/mcp` for AI clients, riding the same authentication as the HTTP API, plus `mcp_writable`
  (off by default) to additionally expose the MCP print/reprint tools.
- Wrapper: adds the `editor_default_mode` option (`visual` / `yaml`) to choose which surface
  the template studio opens first.

(0.11.0–0.16.0 were tag-only base-image bumps with no wrapper changes.)

## 0.10.0

- Wraps labelito 0.10.0: print/preview API calls can now carry a full template body inline
  (on-the-fly labels) instead of referencing a saved template.
- Wrapper: adds the `inline_templates_enabled` option (off by default) to gate the inline
  template feature; it rides the same authentication as other write endpoints.
- Wrapper: mounts custom fonts and icons from the add-on config folder (`fonts/`, `icons/`),
  picked up alongside labelito's bundled defaults.
- Wrapper: adds the missing `history_keep_entries` / `history_prune_at_entries` labels to the
  configuration UI (previously shown with raw option keys).

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
