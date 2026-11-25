#!/bin/sh
# Runs from /docker-entrypoint.d/ before nginx starts (stock nginx image).
# Writes the runtime API config the built app reads from /config.js.
# API_URL is the PUBLIC backend URL the browser can reach, e.g.
#   http://localhost:8002                 (local Docker)
#   https://diagnoflow-api.onrender.com   (Render)
# Leave it empty to call the same origin (/api/...) instead.
set -eu
api_url="${API_URL:-}"
# URLs do not contain single quotes; escape backslashes just in case.
api_url_escaped=$(printf '%s' "$api_url" | sed 's/\\/\\\\/g')
mkdir -p /usr/share/nginx/html
printf "window.__ENV__ = { API_URL: '%s' };\n" "$api_url_escaped" > /usr/share/nginx/html/config.js
