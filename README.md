<div align="center">

<a href="https://github.com/chiva/labelito"><img src="https://raw.githubusercontent.com/chiva/labelito/main/site/assets/labelito-logo.svg" alt="labelito" width="200"></a>

# labelito Home Assistant Add-on

*Self-hosted label printing for Brother QL printers — one-click in Home Assistant OS.*<br>
lah-beh-LEE-toh · `/la.beˈli.to/` · a Spanish diminutive of "label"

[![Builder](https://github.com/chiva/addon-labelito/actions/workflows/builder.yaml/badge.svg)](https://github.com/chiva/addon-labelito/actions/workflows/builder.yaml)
[![License: MIT](https://img.shields.io/github/license/chiva/addon-labelito)](LICENSE)

</div>

Run [labelito](https://github.com/chiva/labelito) as a one-click Home Assistant add-on, with
ingress-authenticated access and Supervisor discovery.

## The labelito ecosystem

labelito is three pieces. You do **not** need all of them — pick what fits your setup:

| Project | What it is | Use it when |
| --- | --- | --- |
| [`labelito`](https://github.com/chiva/labelito) | The label-printing **service** (the engine). | You want to run it anywhere with Docker. |
| **`addon-labelito`** (this repo) | Packages that service as a **Home Assistant add-on**. | You run Home Assistant OS/Supervised and want one-click install. |
| [`ha-labelito`](https://github.com/chiva/ha-labelito) | HACS **integration** — entities, a `labelito.print` service, and voice. | You want to print from automations, dashboards, or Assist. |

This add-on **announces itself** to the Supervisor, so `ha-labelito` sets up in a single
confirmation click once both are installed.

## Installation

[![Add repository to my Home Assistant](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Fchiva%2Faddon-labelito)

1. Click the badge above (or add `https://github.com/chiva/addon-labelito` under
   **Settings → Add-ons → Add-on store → ⋮ → Repositories**).
2. Install the **labelito** add-on from the store.
3. Set your printer model and URI in the add-on configuration, then start it.
4. Open the web UI from the sidebar (ingress — no port or token setup needed).

### Supported architectures

`aarch64` (Home Assistant Green, Home Assistant Yellow, and Raspberry Pi 3/4/5 running 64-bit
Home Assistant OS) and `amd64`. 32-bit installs (`armv7`/`armhf`) are not supported — modern
Home Assistant hardware and the official Raspberry Pi HAOS images are all 64-bit.

Full configuration, security, and printer setup live in the add-on's **Documentation** tab
([DOCS.md](labelito/DOCS.md)), with deeper guides in [`docs/`](docs/).

## Add-ons

| Add-on | Description |
| --- | --- |
| [labelito](labelito/) | Design label templates once, print them from the web UI, the HTTP API, or Home Assistant. |

## How this repository works

The add-on is a thin wrapper around the upstream `ghcr.io/chiva/labelito` image and is published
as `ghcr.io/chiva/labelito-addon`. The add-on version always equals the wrapped labelito version;
Renovate bumps the base image and manifest in lockstep on every release. See
[`docs/release-process.md`](docs/release-process.md).

## License

This repository (the wrapper) is [MIT](LICENSE). The wrapped labelito image is
[GPL-3.0-or-later](https://github.com/chiva/labelito/blob/main/LICENSE) — it is pulled at build
time, not vendored here.
