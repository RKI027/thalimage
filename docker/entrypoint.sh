#!/bin/sh
set -e

PUID="${PUID:-1000}"
PGID="${PGID:-1000}"

# Create group and user if they don't already exist
if ! getent group thalimage >/dev/null 2>&1; then
    groupadd -g "$PGID" thalimage
fi
if ! getent passwd thalimage >/dev/null 2>&1; then
    useradd -u "$PUID" -g "$PGID" -d /data -s /bin/sh thalimage
fi

# Ensure data dir is owned by the app user
chown -R "$PUID:$PGID" /data

exec gosu thalimage "$@"
