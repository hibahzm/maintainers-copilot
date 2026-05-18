#!/usr/bin/env sh
set -eu

if [ -f alembic.ini ]; then
  exec alembic upgrade head
fi

echo "Alembic baseline not configured yet; migrate service scaffold is present."
