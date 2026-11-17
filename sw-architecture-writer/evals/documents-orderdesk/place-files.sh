#!/usr/bin/env bash
# Builds the orderdesk sample repository (stage: code) in the current directory.
set -eu
fixtures="$(cd "$(dirname "$0")" && pwd -P)/../../../eval-fixtures"
if [ ! -x "$fixtures/scaffold.sh" ]; then
  echo "eval-fixtures/ not found next to the skill folders; run the evals from a checkout of the whole repository" >&2
  exit 1
fi
exec "$fixtures/scaffold.sh" code
