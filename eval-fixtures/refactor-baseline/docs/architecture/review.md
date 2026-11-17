# orderdesk — architecture review

- **Reviewed at commit:** `__COMMIT__` (__DATE__)
- **Input:** `docs/architecture/architecture.md`; every finding checked against the code.

## Raised before the table

Two confirmed findings an outside caller can use today: `GET /admin/export` returns every customer and order with no token (#9), and the PayFast live API key is committed in `orderdesk/payments.py:5` (#10; rotate it — it stays in git history).

## Findings

| # | Dimension | Improvement | Evidence | Benefit | Risk | Cost | Selected |
|---|-----------|-------------|----------|---------|------|------|----------|
| 1 | Testability | Extract the pricing rules (subtotal, discount, coupon, tax, shipping) from `create_order` into a pure function with no DB, payment, clock or UUID | service.py:12, confirmed | High | Medium | Low | **yes** |
| 2 | Simplicity | Inline `DiscountStrategy` / factory — one implementation | pricing_rules.py:6, confirmed | Low | Low | Low | no |
| 3 | Simplicity | Delete unused `ENABLE_LEGACY_ROUNDING` | config.py:15, confirmed | Low | Low | Low | no |
| 4 | Robustness | Validate the order payload at the HTTP boundary (`customer_id`, `items` with `sku`/`qty`/`unit_cents`, `card_number`) and return a 400 with field errors instead of a 500 | server.py:50, service.py:13, confirmed | Medium | Medium | Low | **yes** |
| 5 | Robustness | Stop returning tracebacks to clients | server.py:48, 66, confirmed | Medium | Low | Low | no |
| 6 | Robustness | Add a timeout and backoff to PayFast calls | payments.py:12, confirmed | High | Medium | Low | no |
| 7 | Robustness | Charge-then-insert dual write: record a pending order before charging | service.py:48–61, confirmed | High | High | Medium | no |
| 8 | Observability | Replace `print` with structured logging and a request id; stop logging card numbers | server.py:56, payments.py:29, confirmed | Medium | Low | Low | no |
| 9 | Security | Require the API token on `GET /admin/export` | server.py:28, confirmed | High | Low | Low | **yes** |
| 10 | Security | Move the PayFast key to the environment and rotate it | payments.py:5, confirmed | High | Low | Low | no |
| 11 | Security | Parameterize the customer-name query | db.py:39, confirmed | High | Low | Low | no |

## Goals of the selected items

- **#1** — the pricing rules can be unit-tested without a database, the payment API, the clock or UUIDs; `create_order` shrinks to orchestration. Behavior must not change.
- **#4** — malformed order payloads are rejected with a 400 before any service code runs.
- **#9** — `/admin/export` answers 401 without a valid `X-Api-Token`.

## Plan

- **Phase 0 — safety net.** `create_order` had no tests: pin it with `tests/test_orders_characterization.py` (done, included at this commit). Every later phase keeps it green with no assertion changed.
- **Phase 1 — #9.** Add the token check to the `/admin/export` branch. Validate: request without token returns 401. Rollback: revert the commit.
- **Phase 2 — #1.** Move the pricing block into `orderdesk/pricing.py: compute_totals(items, vip, coupon)`; `create_order` calls it. Validate: characterization suite unchanged and green; new unit tests for the pure function. Rollback: revert.
- **Phase 3 — #4.** Add `validate_order_payload` in `server.py`, called before `create_order`. Validate: tests for missing/wrong-typed fields return 400. Rollback: revert.

## Accepted risk (security findings not selected)

- #10 — anyone with repo access can charge and refund through the PayFast account.
- #11 — a caller with a token can read or alter other tables through the `customer` query parameter.
