# Eval fixtures

A small sample service with known, planted problems, and the scripts that turn it into the starting state each eval case needs. The eval cases themselves live with each skill, under `sw-*/evals/`.

## The sample: `orderdesk/`

A single-process Python order service (standard library only, runs anywhere Python 3 does): an HTTP API, SQLite storage, a payment call to a fictional PayFast API at a `.example` host that never resolves, an event log written by a background thread, and a top-customers report.

It is deliberately flawed. This is the answer key the graders are written against — the skills under test never see this file, because each run gets a copy of `orderdesk/` only.

| Area | Planted problem | Where |
|------|-----------------|-------|
| Fidelity | README claims Redis caching; the code uses a dict | `README.md`, `orderdesk/cache.py` |
| Simplicity | `create_order` does pricing, payment, persistence and events in one function (CC 16) | `orderdesk/service.py:12` |
| Simplicity | Strategy interface and factory with one implementation; an unused config flag | `orderdesk/pricing_rules.py`, `orderdesk/config.py` |
| Simplicity | Token check repeated per route branch, and missing from one | `orderdesk/server.py` |
| Testability | Pricing rules tangled with clock, UUID, payment and SQL; global connection; thread started at import | `service.py`, `db.py`, `events.py` |
| Robustness | Card charged before the order row is written; no timeout and no backoff on payment calls; tracebacks returned to clients; swallowed errors; unbounded cache and queue | `service.py`, `payments.py`, `server.py`, `events.py`, `cache.py` |
| Observability | `print` only; no request ids; request bodies and card numbers logged | `server.py:56`, `payments.py:29` |
| Security | `GET /admin/export` needs no token; string-built SQL; a (fake) live API key in source; default API token fallback | `server.py:28`, `db.py:39`, `payments.py:5`, `config.py` |
| Business logic | Negative refund amounts and negative unit prices are accepted; a VIP using `WELCOME10` gets "unknown coupon" | `service.py` |
| Behavior to pin | Tax is truncated, not rounded; a partial refund leaves the order `OPEN` | `service.py` |
| Performance | The report rescans all orders once per customer (about a second at 2,000 customers / 20,000 orders) | `orderdesk/reports.py:32` |
| Performance decoy | `format_report_row` is more complex than the slow function but runs ten times per report | `orderdesk/reports.py:4` |

`tools/complexity.py` measures size and cyclomatic complexity with the standard library, so before/after numbers are reproducible without installing anything.

## Stages: `scaffold.sh`

`scaffold.sh <stage>` builds a git repository in the current directory:

| Stage | Contents | Used by |
|-------|----------|---------|
| `code` | the service, one commit | writer, security scanner |
| `docs` | plus `docs/architecture/architecture.md` (from `docs-overlay/`) | reviewer, test-suite generator, optimizer |
| `refactored` | plus a review, a characterization test, and three commits implementing part of the review (from `refactor-baseline/` and `refactor-after/`) | visualizer |

The `refactored` stage is built to be judged: of the three selected improvements, the pricing extraction landed (but most of the complexity moved into the new function), payload validation is partial, the admin-export token check was never done, and a commit titled "Update order tests" quietly changed the expected tax from truncated to rounded.

## Running the evals

Each case is a folder: `prompt.md` (the request), `case.yaml` (what a good result looks like), `graders/` (one checkable statement per file), and `place-files.sh` (calls `scaffold.sh`). The scripts find this folder relative to the skill folders, so run from a checkout of the whole repository, not from a single copied skill.

With Claude Code (v2.1.269 or later), from a skill folder:

    cd sw-architecture-reviewer
    claude plugin eval . --scaffold --allow-tools Write,Edit,Bash

That runs each case with and without the skill and writes a report under `evals/results/`. These are real, billed model runs — several long agent sessions per case; add `--runs 1` and `--case <name>` to start small.

The cases can also be run by hand: make an empty directory, run the case's `place-files.sh` in it, give an agent the prompt, and check the result against the graders.

The runs are non-interactive, so the skills cannot show their selection menu. The cases are written for that: they either expect the run to stop and ask, or put the selection in the prompt.
