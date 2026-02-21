#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="${IMAGE_NAME:-symlink-editor}"
CONTAINER_NAME="${CONTAINER_NAME:-symlink-editor}"
HOST_PORT="${HOST_PORT:-8080}"
FILMS_DIR="${FILMS_DIR:-$PWD/films}"

mkdir -p "$FILMS_DIR"

docker build -t "$IMAGE_NAME" .

docker run --rm \
  --name "$CONTAINER_NAME" \
  -p "$HOST_PORT":8080 \
  -e FILMS_ROOT=/data/3d_films \
  -e SYMLINK_EDITOR_HOST=0.0.0.0 \
  -e SYMLINK_EDITOR_PORT=8080 \
  -v "$FILMS_DIR":/data/3d_films \
  "$IMAGE_NAME"
