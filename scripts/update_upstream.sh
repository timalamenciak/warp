#!/usr/bin/env bash
# Re-vendor the upstream schemas at pinned commits and record what was taken.
#
#   scripts/update_upstream.sh [SEPIO_REF] [CAMO_REF]
#
# REF can be a branch, tag or commit (default: main). Files in
# src/warp/schema/upstream/ are never edited by hand: changes to
# SEPIO go upstream as pull requests; EcoWeaver changes go in warp.yaml.
set -euo pipefail

SEPIO_REPO="https://github.com/sepio-framework/sepio-linkml"
CAMO_REPO="https://github.com/timalamenciak/causalmosaic"
SEPIO_REF="${1:-main}"
CAMO_REF="${2:-main}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/src/warp/schema/upstream"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

fetch() {  # repo ref dir
  git clone -q "$1" "$3"
  git -C "$3" checkout -q "$2"
  git -C "$3" rev-parse HEAD
}

SEPIO_SHA="$(fetch "$SEPIO_REPO" "$SEPIO_REF" "$WORK/sepio")"
CAMO_SHA="$(fetch "$CAMO_REPO" "$CAMO_REF" "$WORK/camo")"

cp "$WORK/sepio/src/sepio_linkml/schema/sepio_classes.yaml" "$DEST/sepio_classes.yaml"
cp "$WORK/sepio/LICENSE" "$DEST/SEPIO_LICENSE"
cp "$WORK/camo/causalmosaic.yaml" "$DEST/causalmosaic.yaml"

cat > "$DEST/UPSTREAM.md" <<EOF
# Vendored upstream schemas

Do not edit these files. Re-vendor with \`scripts/update_upstream.sh\`.

| File | Source | Commit |
|---|---|---|
| sepio_classes.yaml | $SEPIO_REPO (src/sepio_linkml/schema/) | $SEPIO_SHA |
| causalmosaic.yaml | $CAMO_REPO | $CAMO_SHA |

SEPIO is Apache-2.0 (see SEPIO_LICENSE). CAMO is CC0.
Vendored on $(date -u +%Y-%m-%d).
EOF

echo "SEPIO $SEPIO_SHA"
echo "CAMO  $CAMO_SHA"
echo "Now run: make validate"
