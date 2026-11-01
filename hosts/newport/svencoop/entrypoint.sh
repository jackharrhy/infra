#!/bin/sh
set -eu

: "${SVENCOOP_PASSWORD:?Render secrets/server.enc.yaml into .runtime-secrets/server.env}"
: "${SVENCOOP_DOWNLOAD_URL:?Set the public HTTP FastDL origin}"
case "$SVENCOOP_PASSWORD" in
  *[!a-zA-Z0-9._-]*) echo 'Password must use letters, numbers, dot, underscore or dash.' >&2; exit 1 ;;
esac
case "$SVENCOOP_DOWNLOAD_URL" in
  http://*) ;;
  *) echo 'FastDL must use an HTTP URL.' >&2; exit 1 ;;
esac
case "$SVENCOOP_DOWNLOAD_URL" in
  *[!a-zA-Z0-9:./_-]*) echo 'Unsupported characters in FastDL URL.' >&2; exit 1 ;;
esac

umask 077
printf 'sv_password "%s"\nsv_downloadurl "%s"\n' \
  "$SVENCOOP_PASSWORD" "$SVENCOOP_DOWNLOAD_URL" > session.cfg
printf '%s\n' "${SVENCOOP_ADMINS:-}" > jack-admins.txt
chmod 600 session.cfg jack-admins.txt
exec "$@"
