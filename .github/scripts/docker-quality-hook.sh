#!/usr/bin/env bash
set -euo pipefail

container=stockvalue-exporter-pr-quality-check

case "${1:-}" in
  before)
    ;;
  after)
    : "${LOCAL_IMAGE:?A template-built image is required}"
    docker run --rm --entrypoint sh "$LOCAL_IMAGE" -eu -c '
      test "$(id -u)" -eq 10001
      test "$(id -g)" -eq 10001
      test "$HOME" = /home/appuser
      test "$XDG_CACHE_HOME" = /home/appuser/.cache
      test -w "$XDG_CACHE_HOME"
      test ! -w /app
      touch "$XDG_CACHE_HOME/.write-test"
    '
    docker run --detach --name "$container" \
      --publish 127.0.0.1:19100:9100 "$LOCAL_IMAGE"
    for ((attempt = 0; attempt < 30; attempt++)); do
      if curl --fail --silent --max-time 2 http://127.0.0.1:19100/health >/dev/null; then
        exit 0
      fi
      sleep 1
    done
    docker logs "$container" >&2 || true
    echo "Container did not become healthy" >&2
    exit 1
    ;;
  cleanup)
    docker rm -f "$container" >/dev/null 2>&1 || true
    ;;
  *)
    echo "Usage: $0 {before|after|cleanup}" >&2
    exit 2
    ;;
esac
