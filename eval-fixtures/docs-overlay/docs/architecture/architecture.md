# orderdesk — architecture

- **Commit:** `__COMMIT__` (__DATE__)
- **Scope:** whole repository, every source file read in full.
- **Complexity measured with:** `python3 tools/complexity.py orderdesk` (cyclomatic = 1 + decision points; LOC excludes signature, blanks, comments).
- **Tests:** `python3 -m unittest discover -s tests` (unittest; one test file).

Note: `README.md` says Redis is used for caching. There is no Redis client in the code; the customer cache is an in-process dict (`orderdesk/cache.py:3`). The diagrams show what the code does.

## 1. Runtime architecture

```
                                        ┌───────────────────────────────────────────┐
 ┌──────────┐ HTTP :8080, X-Api-Token   │ orderdesk process (orderdesk/server.py:72) │
 │ API      │ POST /orders              │                                           │
 │ client   │ POST /orders/{id}/refund  │  Handler ─▶ service ─▶ db ────────────────┼──▶ SQLite file
 │          │ GET  /orders[/{id}]       │  server.py   service.py  db.py:10         │    ORDERDESK_DB
 │          │ GET  /report/top-customers│     │           │                         │    customers, orders,
 └──────────┘ ─────────────────────────▶│     │           ├─▶ cache (dict)          │    order_items
                                        │     │           │   cache.py:3            │
 ┌──────────┐ HTTP :8080, NO token      │     │           ├─▶ payments ─────────────┼──▶ PayFast API (external)
 │ Operator │ GET /admin/export         │     │           │   payments.py:12        │    HTTPS POST /v1/charges
 │ (anyone) │ ─────────────────────────▶│     ▼           │                         │    HTTPS POST /v1/refunds
 └──────────┘                           │  reports ───────┘                         │
                                        │  reports.py     ├─▶ events queue (list)   │
                                        │                 │   events.py:7           │
                                        │                 ▼                         │
                                        │  drain thread (events.py:14, started at   │
                                        │  import, events.py:27) ───────────────────┼──▶ events.log (JSON lines)
                                        └───────────────────────────────────────────┘    ORDERDESK_EVENTS_LOG
```

- One process, `ThreadingHTTPServer` (a thread per request) plus one daemon thread draining the event queue.
- A single shared SQLite connection, opened lazily, `check_same_thread=False` (`db.py:13`).
- `events.log` is the only "publish" target; nothing in the repo consumes it (?) — presumably read by the fulfilment team's tooling.

## 2. Source code architecture (Python)

```
orderdesk/
├── server.py   ─▶ service.py ─▶ cache.py ─▶ db.py ─▶ (sqlite)
│      │              ├─▶ db.py
│      │              ├─▶ payments.py ─▶ (PayFast HTTPS)
│      │              ├─▶ events.py   ─▶ (events.log)
│      │              └─▶ pricing_rules.py
│      ├─▶ reports.py ─▶ db.py
│      └─▶ db.py                (GET /orders queries the db directly, skipping service)
└── config.py   ◀─ imported by server, db, service, events, pricing_rules, reports
scripts/seed.py ─▶ orderdesk.db  (demo / load data)
tools/complexity.py              (measurement only)
tests/test_pricing_rules.py ─▶ orderdesk.pricing_rules
```

| Module | Depends on (fan-out) | Depended on by (fan-in) | Notes |
|--------|----------------------|-------------------------|-------|
| server | service, reports, db, config (4) | — | Calls `db` directly for `GET /orders`, skipping `service`. Token check written out per route branch. |
| service | cache, config, db, events, payments, pricing_rules (6) | server (1) | Highest fan-out; holds the pricing rules as well as the orchestration. |
| reports | db, config (2) | server (1) | |
| cache | db (1) | service (1) | |
| db | config (1) | server, service, reports, cache (4) | Returns raw rows; `server` and `service` pass them to clients as-is. |
| payments | — | service (1) | |
| events | config (1) | service (1) | Starts a thread at import. |
| pricing_rules | config (1) | service (1) | |
| config | — | server, service, db, events, pricing_rules, reports (6) | Constants only. |

No dependency cycles. Co-change: single-commit history, no signal.

Wiring: `Dockerfile` copies `orderdesk/` and `scripts/`, sets `ORDERDESK_DB=/data/orderdesk.db`, runs `python3 -m orderdesk.server`. No compose file, CI, or IaC.

## 3. Function complexity map

Scope: all non-trivial functions in `orderdesk/`. Churn: single-commit history, so no signal.

| File:Line | Function | LOC | CC | Tests | Notes |
|-----------|----------|-----|----|-------|-------|
| orderdesk/service.py:12 | `create_order` | 54 | 16 | none | **Hotspot.** Pricing, discount, coupon, tax and shipping rules inline with the payment call, clock, UUID, SQL inserts and event publish. |
| orderdesk/reports.py:4 | `format_report_row` | 25 | 11 | none | Branchy formatting; called at most `MAX_REPORT_ROWS` (10) times per report. |
| orderdesk/server.py:25 | `do_GET` | 23 | 10 | none | Routing by if/elif; auth check repeated per branch; `/admin/export` branch has none. |
| orderdesk/reports.py:32 | `top_customers` | 20 | 8 | none | Loads all orders, then scans them once per customer; one customer query per customer. |
| orderdesk/server.py:50 | `do_POST` | 16 | 7 | none | Routing; logs the full request body. |
| orderdesk/service.py:69 | `refund_order` | 14 | 4 | none | Refund via PayFast, then DB update, then event. |
| orderdesk/events.py:14 | `_drain_forever` | 9 | 4 | none | Swallows write errors. |
| orderdesk/payments.py:12 | `_post` | 13 | 3 | none | Three immediate retries, no timeout. |
| orderdesk/db.py:10 | `conn` | 21 | 2 | none | Global connection, creates schema on first use. |
| orderdesk/pricing_rules.py:13 | `BulkDiscountStrategy.discount_cents` | 3 | 2 | tests/test_pricing_rules.py | The only tested function. |

## 4. Sequence diagrams

### 4.1 Create order

```
API client      Handler(do_POST)   service.create_order    cache/db        PayFast API      events
   │ POST /orders    │                   │                    │                │              │
   │────────────────▶│ check X-Api-Token │                    │                │              │
   │                 │ create_order(body)│                    │                │              │
   │                 │──────────────────▶│ customer(id)       │                │              │
   │                 │                   │───────────────────▶│ SELECT customers (cached)     │
   │                 │                   │ price: subtotal, discount, coupon, tax, shipping   │
   │                 │                   │ POST /v1/charges (card, total)      │              │
   │                 │                   │────────────────────────────────────▶│              │
   │                 │                   │◀────────────────────────────────────│ charge id    │
   │                 │                   │ INSERT orders, order_items; COMMIT  │              │
   │                 │                   │───────────────────▶│                │              │
   │                 │                   │ publish order.created               │              │
   │                 │                   │───────────────────────────────────────────────────▶│
   │                 │◀──────────────────│ {id, status PAID, totals}           │              │
   │◀────────────────│ 201               │                    │                │              │
```

The card is charged before the order row is written; a failure between the two leaves a charge with no order.

### 4.2 Refund

```
API client      Handler(do_POST)   service.refund_order      db            PayFast API      events
   │ POST /orders/{id}/refund {amount_cents}                  │                │              │
   │────────────────▶│──────────────────▶│ SELECT order       │                │              │
   │                 │                   │───────────────────▶│                │              │
   │                 │                   │ POST /v1/refunds   │                │              │
   │                 │                   │────────────────────────────────────▶│              │
   │                 │                   │ UPDATE orders SET refunded_cents, status           │
   │                 │                   │───────────────────▶│                │              │
   │                 │                   │ publish order.refunded              │              │
   │                 │                   │───────────────────────────────────────────────────▶│
   │◀────────────────│ 200 {status}      │  status = REFUNDED if fully refunded, else OPEN    │
```

### 4.3 Top-customers report

```
API client      Handler(do_GET)    reports.top_customers            db
   │ GET /report/top-customers           │                           │
   │────────────────▶│──────────────────▶│ SELECT * FROM orders      │
   │                 │                   │──────────────────────────▶│
   │                 │                   │ per customer: scan all orders, SELECT customer
   │                 │                   │──────────────────────────▶│  (once per customer)
   │                 │                   │ sort, format top 10       │
   │◀────────────────│ 200 [rows]        │                           │
```

### 4.4 Admin export

```
Operator (no token)   Handler(do_GET)    reports.export_all          db
   │ GET /admin/export     │                   │                      │
   │──────────────────────▶│──────────────────▶│ SELECT customers     │
   │                       │                   │ per customer: orders by name (string-built LIKE)
   │◀──────────────────────│ 200 all customers, emails and orders     │
```
