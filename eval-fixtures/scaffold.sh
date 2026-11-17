#!/usr/bin/env bash
# Builds the orderdesk sample repository in the current directory for an eval case.
#
#   scaffold.sh code        the service as a one-commit git repo
#   scaffold.sh docs        code + docs/architecture/architecture.md
#   scaffold.sh refactored  docs + a review, a characterization test, and three
#                           commits that implement part of the review
set -eu
stage="${1:-code}"
here="$(cd "$(dirname "$0")" && pwd -P)"
g() { git -c user.name="Eval Fixture" -c user.email="eval@example.invalid" -c commit.gpgsign=false "$@"; }
stamp() { sed -i.bak "s/__COMMIT__/$1/; s/__DATE__/$2/" "$3" && rm -f "$3.bak"; }

cp -R "$here/orderdesk/." .
g init -q -b main .
g add -A && g commit -q -m "orderdesk service"
[ "$stage" = code ] && exit 0

sha="$(g rev-parse --short HEAD)"; day="$(date +%Y-%m-%d)"
cp -R "$here/docs-overlay/." .
stamp "$sha" "$day" docs/architecture/architecture.md
g add -A && g commit -q -m "Add architecture docs"
[ "$stage" = docs ] && exit 0

cp -R "$here/refactor-baseline/." .
stamp "$sha" "$day" docs/architecture/review.md
g add -A && g commit -q -m "Add architecture review and characterization tests for create_order"

cp "$here/refactor-after/orderdesk/pricing.py" orderdesk/pricing.py
cp "$here/refactor-after/orderdesk/service.py" orderdesk/service.py
cp "$here/refactor-after/tests/test_pricing.py" tests/test_pricing.py
g add -A && g commit -q -m "Extract pricing rules into pricing.compute_totals (#1)"
cp "$here/refactor-after/tests/test_orders_characterization.py" tests/test_orders_characterization.py
g add -A && g commit -q -m "Update order tests"
cp "$here/refactor-after/orderdesk/server.py" orderdesk/server.py
g add -A && g commit -q -m "Validate order payload at the HTTP boundary (#4)"
