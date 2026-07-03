# Access and security

The add-on has two access paths. For a typical homelab, **leave the defaults** — ingress-only is
the safe choice.

## Ingress (default)

The sidebar panel is authenticated by Home Assistant itself. No host port is exposed and no API
token is needed. Home Assistant points labelito's `PROXY_PATH_HEADER` at `X-Ingress-Path`, so
generated URLs stay correct behind the ingress proxy.

## Direct port (opt-in)

Map host port `8765` in the add-on's **Network** section only if something *outside* Home
Assistant needs the HTTP API (a script on another host, say).

- The add-on **refuses to start** if the port is mapped without an `api_token` set — an open port
  with no token would accept anyone on your LAN.
- API clients authenticate with `Authorization: Bearer <api_token>`.

## The internal `hassio` network

Other add-ons on the internal `hassio` Docker network can reach the service without a token when
`api_token` is unset. This is an accepted trade-off of the ingress-only default — the worst case
is a misbehaving add-on wasting labels. Set an `api_token` to close it.

## What to set when

| Scenario | `api_token` | Host port |
| --- | --- | --- |
| Ingress only (recommended) | unset | closed |
| External API client on your LAN | **required** | mapped |
| Hardening against other add-ons | set | closed |
