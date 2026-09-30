#!/usr/bin/env bash
# Push this repo to a Hugging Face Space (Docker SDK) and redeploy it.
#
# Usage:
#   ./deploy/push-to-hf.sh <USER>/<SPACE>
# Example:
#   ./deploy/push-to-hf.sh alice/udyogsetu

set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <HF_USER>/<SPACE>" >&2
  echo "Example: $0 alice/udyogsetu" >&2
  exit 1
fi

SPACE="$1"

if [[ "$SPACE" != */* ]]; then
  echo "Expected SPACE as <user>/<space>, got: $SPACE" >&2
  exit 1
fi

if git remote get-url hf >/dev/null 2>&1; then
  echo "Remote 'hf' already exists: $(git remote get-url hf)"
  echo "NOTE: resetting it to point at the requested space."
fi

git remote remove hf >/dev/null 2>&1 || true
git remote add hf "https://huggingface.co/spaces/$SPACE"
echo "Pushing 'main' to https://huggingface.co/spaces/$SPACE"
git push hf main