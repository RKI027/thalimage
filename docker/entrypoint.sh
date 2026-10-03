#!/bin/sh
set -e

PUID="${PUID:-1000}"
PGID="${PGID:-1000}"

# Match the numeric ids rather than the account name: the id is what has
# to line up with the ownership of the mounted image folders, and a GID
# like 1000 usually already belongs to some other group in the base image.
getent group "$PGID" >/dev/null 2>&1 || groupadd -g "$PGID" thalimage
getent passwd "$PUID" >/dev/null 2>&1 || useradd -u "$PUID" -g "$PGID" -d /data -s /bin/sh thalimage

# A freshly created bind mount is owned by root; the app needs to write
# the database and both cache trees. Previews in particular are generated
# lazily on first request, so this is request-time write access, not just
# scan-time. mkdir covers the case where nothing is mounted at all.
mkdir -p /data
chown -R "$PUID:$PGID" /data

# gosu does not reliably carry HOME across the privilege drop, and the
# optional config.toml is looked up under it.
export HOME=/data

exec gosu "$PUID:$PGID" "$@"
