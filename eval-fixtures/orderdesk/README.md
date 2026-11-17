# orderdesk

A small order-taking service: create orders, charge the customer through the
PayFast payment API, refund orders, and run a top-customers report.

- HTTP API on port 8080 (`python3 -m orderdesk.server`)
- SQLite for storage
- Redis for caching customer lookups
- Order events are published for the fulfilment team

## Run

    python3 scripts/seed.py            # small demo data set
    python3 -m orderdesk.server

## Complexity

    python3 tools/complexity.py orderdesk

## Test

    python3 -m unittest discover -s tests
