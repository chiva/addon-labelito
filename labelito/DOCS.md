# labelito

Self-hosted label printing for Brother QL printers. Design label templates once in YAML,
then print them from the web UI, the HTTP API, or Home Assistant automations. This add-on
wraps the upstream [labelito](https://github.com/chiva/labelito) image — the add-on
version always equals the wrapped labelito version.

## Quick start

1. Set **Printer model** and **Printer URI** in the configuration tab.
2. Start the add-on and open **labelito** from the sidebar.
3. Pick a template, fill its fields, check the live preview, print.

## Configuration

| Option | Default | Description |
| --- | --- | --- |
| `model` | `QL-810W` | Brother QL model connected to this add-on. labelito cross-checks it against what the printer reports and flags a mismatch. |
| `printer_uri` | `tcp://192.168.1.100:9100` | Network printers: `tcp://<ip>:9100`. USB printers: `usb://0x04f9:0x209c` (`vendorId:productId` — find yours under **Settings → System → Hardware** or with `lsusb`). |
| `api_token` | *(unset)* | Bearer token protecting the HTTP API. Optional while access is ingress-only; **required if you open the host port** (see below). |
| `editor_enabled` | `false` | Enable the YAML template studio, including saving templates into this add-on's config folder. |
| `default_language` | `en` | Language for label chrome text (dates, headings) unless a print request overrides it. |
| `log_level` | `info` | Web-server log verbosity. |

## Access and security

- **Ingress (default):** the sidebar panel is authenticated by Home Assistant. No port is
  exposed and no token is needed — leave it this way for a typical setup.
- **Direct port (opt-in):** map host port `8765` only if something outside Home Assistant
  needs the API; the add-on then **requires** an `api_token`.

Full details, including the internal `hassio` network trade-off and a when-to-set-what table,
are in [docs/security.md](https://github.com/chiva/addon-labelito/blob/main/docs/security.md).

## Templates

User templates live in this add-on's config folder,
`/addon_configs/<repo>_labelito/templates/` (editable via the Samba, SSH, or Studio Code
Server add-ons). On first start the folder is seeded with the bundled example templates.
Changes survive add-on updates and restarts.

With `editor_enabled: true` the **Studio** tab edits and saves these files directly from
the browser, with a live draft preview.

Template format, fields, computed dates, icons, and QR codes are documented in the
[labelito template guide](https://github.com/chiva/labelito#templates).

## Printers

- **Network (recommended):** `tcp://<ip>:9100`. Give the printer a static IP or DHCP
  reservation. labelito also reads live status over SNMP (media, errors, label counter).
- **USB:** `usb://<vendorId>:<productId>` (e.g. `usb://0x04f9:0x209c` for a QL-810W).

Finding USB ids, DHCP tips, and the SNMP status details are in
[docs/networking-and-usb.md](https://github.com/chiva/addon-labelito/blob/main/docs/networking-and-usb.md).

## Data

Print history (backing the History tab, retry de-duplication, and reprint) is stored
durably in the add-on's private data folder and survives restarts and updates.

## Home Assistant integration

The add-on announces itself to the Supervisor's discovery registry, so the upcoming
`ha-labelito` integration can be set up with one click — printer status sensors, a
`labelito.print` service for automations, and voice intents. Until it ships, automations
can call the HTTP API directly with a `rest_command`.
