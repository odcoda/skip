#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXPECTED_DIR="$SCRIPT_DIR/data/expected"

if [[ ! -d "$EXPECTED_DIR" ]]; then
  echo "Expected directory not found: $EXPECTED_DIR"
  exit 1
fi

accepted=0
while IFS= read -r -d '' corrected; do
  target="${corrected%.corrected}"
  mv "$corrected" "$target"
  echo "accepted: $target"
  accepted=$((accepted + 1))
done < <(find "$EXPECTED_DIR" -type f -name '*.corrected' -print0)

echo "accepted $accepted corrected file(s)"
