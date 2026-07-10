# Thin Home Assistant add-on wrapper around the upstream labelito image: same app, plus an
# entrypoint that translates the add-on's /data/options.json into labelito's environment.
#
# BUILD_FROM is injected per-arch by the Home Assistant builder from build.yaml; the default
# here keeps a plain `docker build` working for local testing. Renovate bumps the tag in
# build.yaml, this default, and config.yaml's `version` together (they must stay in lockstep —
# the Supervisor pulls the wrapper tag named by the manifest).
ARG BUILD_FROM=ghcr.io/chiva/labelito:0.9.0
FROM ${BUILD_FROM}

LABEL org.opencontainers.image.title="labelito add-on" \
      org.opencontainers.image.description="Home Assistant add-on wrapping the labelito label-printing service" \
      org.opencontainers.image.source="https://github.com/chiva/addon-labelito" \
      io.hass.type="addon"

# The upstream image runs as uid 1000, but under the Supervisor the mapped /data, /config,
# and USB device nodes are root-owned — run as root, the add-on convention (the Supervisor
# sandboxes the container).
USER root

COPY run.sh addon_init.py /
RUN chmod 755 /run.sh
CMD ["/run.sh"]
