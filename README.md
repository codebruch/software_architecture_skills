# software_architecture_skills

Six Claude Code skills that work as a pipeline for understanding, protecting, improving, securing, optimizing, and verifying the architecture of an existing codebase.

## Skills

### `sw-architecture-writer`
Reverse-engineers a codebase and documents its architecture as ASCII diagrams plus a function complexity map. Produces four deliverables:

1. **Runtime architecture** — how components interact at runtime (HTTP, SQL, queues, etc.) with actors on the edges.
2. **Source code architecture** — package/module layout, one diagram per language, plus wiring artifacts (Dockerfile, compose, CI, IaC).
3. **Function complexity map** — table of non-trivial functions with file:line, LOC, cyclomatic complexity, git churn, existing test coverage, and hotspot notes.
4. **Sequence diagrams** — important flows, with end users and external systems as actors.

It saves the result to `docs/architecture/architecture.md` with the commit it describes and the exact complexity-measurement command, so the later skills can find it, tell how stale it is, and re-measure the same way.

### `sw-test-suite-generator`
Runs *after* the writer and ideally *before* the reviewer or optimizer: it turns the architecture docs into a **characterization test suite** — tests that pin the codebase's *current* behavior so any larger change that alters it trips an alarm. It's the safety net you put underneath a refactor, migration, or optimization before you start.

- **Cardinal rule** — tests never touch the real database or any production persistence. Every boundary the runtime diagram shows is isolated as either a **local test double** (in-memory fake/stub) or a **dedicated, throwaway test persistence** (Testcontainers, an ephemeral schema, an in-memory engine, or transactional rollback). The harness is **fail-closed**: it refuses to run against a non-test target rather than risk real data.
- **Flows from the docs** — the writer's **sequence diagrams** are the flow inventory, the **runtime diagram** is the boundary inventory, and the **complexity map** is the priority list (dense logic is what a refactor most likely breaks).
- **Characterization, not specification** — assertions encode what the system *actually does today*, bugs and all; the point is to detect *change*, including accidental "fixes". Suspected bugs are surfaced to the user, not silently corrected in an assertion.
- **Deterministic by construction** — frozen clock, seeded randomness, stabilized ordering, no real sleeps. A flaky net gets muted, and a muted net is no net.

It lets the user pick scope via selectable options (aimed at what upcoming changes will touch), builds the isolated harness, captures current behavior by running the code, generates the suite at the right pyramid level (unit tests for hotspots, integration tests for flows), then **runs it green and proves it touched no real persistence**, ending with a coverage map tying each test back to the flow or `file:line` it characterizes.

#### Example

Invoke it after the writer, pointing at the docs:

```
/sw-test-suite-generator   # then: "use the architecture docs in ./docs/architecture, I'm about to refactor the pricing module"
```

**1. It designs the isolation per boundary** (from the runtime diagram) before writing a line of test:

| Boundary | Treatment | Technique | How prod is kept safe |
|----------|-----------|-----------|-----------------------|
| postgres `orders` | dedicated test persistence | Testcontainers Postgres, schema dropped per run | DSN comes only from the container the fixture started; the app's `DATABASE_URL` is never read |
| Kafka `order.created` | local double | in-memory publisher capturing events | no broker client constructed in tests |
| Stripe API | local double | stub server replaying recorded fixtures | base URL overridden; real key never read |
| system clock | local double | frozen/injected clock | — |

**2. It pins current behavior** with a deterministic, isolated characterization test (here matching the repo's `pytest`):

```python
def test_partial_refund_leaves_order_open(orders_db, frozen_clock, fake_stripe):
    # characterizes current behavior of OrderService.refund — services/orders.py:142
    order = given_paid_order(orders_db, total=100_00)

    result = OrderService(orders_db, fake_stripe).refund(order.id, amount=40_00)

    assert result.status == "OPEN"          # pinned as-is: partial refund does NOT close the order
    assert fake_stripe.refunds == [(order.id, 40_00)]
    assert orders_db.get(order.id).refunded_cents == 40_00
```

**3. It ends with a coverage map** tying each test back to the architecture artifact it came from:

| Flow / hotspot (source) | Test | Level | Boundaries isolated |
|-------------------------|------|-------|---------------------|
| Refund flow (sequence diagram §4) | `test_partial_refund_leaves_order_open` | integration | postgres, Stripe, clock |
| `calc_total` (complexity map, CC 14) | `test_calc_total_*` (9 cases) | unit | none (pure) |

...and proves isolation: the suite passes with the real `DATABASE_URL` unset, and the guard rejects any target the harness didn't create itself (a `localhost` check alone isn't trusted — it could be a tunnel to a real database). It also proves the alarm rings: a deliberate change to each pinned function turns a test red before being reverted.

### `sw-architecture-reviewer`
Reads architecture documents (typically the writer's output) and proposes improvements across five dimensions:

- **Simplicity** — kill over-engineering, shrink fat functions, drop dead config.
- **Testability** — separate pure logic from I/O so it can be tested without a stack.
- **Robustness** — input validation, fallbacks, safe failure, memory/race-condition risks.
- **Observability** — OpenTelemetry traces, structured logging, switchable debug mode.
- **Security** — authentication and authorization at every trust boundary, untrusted input kept away from queries/commands/templates, secrets out of code and logs, least-privilege credentials. An architecture-level pass, not a penetration test or dependency audit.

It checks each finding against the code (the docs say where to look; the code says whether it's true), scores **benefit**, **risk**, and **cost**, then lets the user select which to pursue. Only for the selected items it draws the future-state architecture (runtime, source code, sequence diagrams) and produces a phased implementation plan with validation and rollback per phase — opening with a characterization-test phase when the code to be changed is untested. The review is saved to `docs/architecture/review.md` for the visualizer.

The dimensions draw on the familiar design principles and named anti-patterns (coupling and cohesion, god modules, leaky abstractions, cross-cutting concerns copied inline, static state), used critically: a principle is a place to look, never the finding. A finding has to name what the problem costs in this codebase, and the reviewer is told not to prescribe a style, a rewrite, or abstraction for its own sake.

### `sw-security-scanner`
Scans the code itself — a whole repository or just a diff — for general security vulnerabilities, with a checklist drawn from the [OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/): access control, authentication and sessions, injection, browser-facing output, files and parsers, outbound requests, cryptography and secrets, errors and logging, business logic, dependencies, and deployment configuration.

- **Verification over detection** — it maps the attack surface, runs whatever scanners are installed, traces untrusted input from source to sink, and then checks every candidate (is the input really attacker-controlled, is the sink reachable, is there a control upstream?) before it becomes a finding. Dismissed leads are listed with the reason.
- **Rules of engagement** — it reads code and nothing else: no requests to live systems, no testing of credentials it finds, no secret values in the report, no working exploits, no code changes during the scan.
- **A report you can act on** — severity from reachability and impact, the specific fix for this codebase, a regression test per fix, and a plain list of what was *not* covered. Saved to `docs/architecture/security-scan.md`; the user then picks what to fix.

Where the reviewer's security dimension asks whether the *design* puts checks at the right boundaries, the scanner asks whether each line that touches untrusted data is safe.

### `sw-performance-optimizer`
Analyzes the codebase together with its architecture documents to propose **concrete, measured** performance optimizations. It walks a strict priority ladder, cheapest-effective-fix first:

1. **Measure** — profile to find the real bottleneck (90% of time is usually in 5% of the code, and it's rarely the part you'd guess), using the kind of measurement the goal calls for (wall-clock/traces for latency, heap for memory, saturation for throughput), from repeated runs, and never against production without explicit go-ahead. Falls back to static analysis only when no profiler can run, and flags those findings as estimated.
2. **Algorithms & data structures** — the biggest wins: hash-map lookups over list scans, precomputed indexes over nested re-scans, the right container (heap / tree / set), memoization. An O(n²)→O(n log n) swap is ~50,000× at n=1,000,000.
3. **Architectural patterns** — caching, batching, concurrency/parallelism, precompute vs defer, not loading data you don't need, and database indexing.
4. **Hot code** — allocations, copies, cache locality, inside a proven-hot loop.
5. **Language/framework pushdowns** — moving a proven, isolated hot path to C/C++/Rust or a separate microservice, *with the risks each creates* spelled out (FFI/serialization overhead, build/deploy/debug complexity, memory safety, network hop, operational burden).

It scores each optimization by **impact / risk / cost**, lets the user pick, then produces a phased plan where every phase has a reproducible before/after **benchmark** and re-measures between phases (optimizations interact).

### `sw-refactor-visualizer`
Runs *after* the reviewer's improvements (or the optimizer's optimizations) have been implemented, and visualizes the impact. For each implemented item it produces:

- A **before/after mermaid diagram** when the change was structural (split functions, moved modules, added validation/fallback/tracing steps) — skipped when there's no structural footprint.
- A **complexity-reduction table** comparing the affected functions before vs after, with explicit deltas, measured the same way as the baseline — or, for an optimization, a before/after benchmark table on the same workload and command.
- A **verdict** on whether the improvement met its original goal.

It also checks that behavior was preserved (test results, plus any assertions or snapshots that were changed along the way), and ends with a roll-up: aggregate complexity delta, a per-dimension scorecard, and outstanding debt for anything not implemented. The report is saved as markdown so the mermaid renders.

## Install

Symlink or copy each skill folder into a Claude Code skills directory.

Globally (available everywhere):
```bash
ln -s "$(pwd)/sw-architecture-writer"    ~/.claude/skills/
ln -s "$(pwd)/sw-test-suite-generator"   ~/.claude/skills/
ln -s "$(pwd)/sw-architecture-reviewer"  ~/.claude/skills/
ln -s "$(pwd)/sw-security-scanner"       ~/.claude/skills/
ln -s "$(pwd)/sw-performance-optimizer"  ~/.claude/skills/
ln -s "$(pwd)/sw-refactor-visualizer"    ~/.claude/skills/
```

Project-scoped (checked into a specific repo) — copy rather than symlink, since an absolute symlink only resolves on your machine:
```bash
mkdir -p <your-project>/.claude/skills
cp -r sw-*/ <your-project>/.claude/skills/
```

## Shared files

The skills hand work to each other through files, by default under `docs/architecture/` in the target repo:

| File | Written by | Read by |
|------|------------|---------|
| `architecture.md` | writer | all the others |
| `test-coverage-map.md` | test-suite-generator | reviewer, optimizer, visualizer |
| `review.md` | reviewer | visualizer |
| `security-scan.md` | security scanner | reviewer, you |
| `performance.md` | optimizer | visualizer |
| `refactor-report.md` | visualizer | you |

## Usage

The skills auto-trigger from their descriptions, or invoke manually:

```
/sw-architecture-writer
/sw-test-suite-generator
/sw-architecture-reviewer
/sw-security-scanner
/sw-performance-optimizer
/sw-refactor-visualizer
```

Typical pipeline: run the **writer** against an unfamiliar codebase; use the **test-suite-generator** to lay down a characterization safety net over the current behavior *before* changing anything; feed the writer's output to the **reviewer** to plan structural improvements (and/or to the **optimizer** to plan measured performance work); implement the selected ones — with the safety net catching any behavior that drifts; then run the **visualizer** to see the before/after impact and confirm complexity actually dropped. The **test-suite-generator** is what makes the bigger changes safe to make: it pins existing behavior so a refactor, migration, or optimization can't quietly regress it, and it does so without ever touching the real database. The **security scanner** is independent of the rest — run it on the whole repository before a release, or on a branch before merging. The **optimizer** is independent of the reviewer — reach for it whenever the goal is speed, latency, or resource cost rather than structure, using the writer's complexity map as its starting point.

## Evals

Each skill has eval cases under `sw-*/evals/`, all run against one small sample service with known, planted problems in `eval-fixtures/` — so a result can be checked against an answer key instead of by impression. See [eval-fixtures/README.md](eval-fixtures/README.md) for what is planted and how to run them.

| Skill | Case | What it checks |
|-------|------|----------------|
| writer | `documents-orderdesk` | all four deliverables, saved with commit and method; real boundaries drawn; the README's false Redis claim not believed |
| reviewer | `reviews-orderdesk` | findings verified and scored; the open admin endpoint raised first; the secret not reproduced; stops for the user's choice |
| reviewer | `plans-selected-improvements` | diagrams only for what was selected; safety-net phase first; unselected security findings kept as accepted risk |
| test-suite generator | `pins-order-flows` | passing suite with payment and database isolated; quirks pinned, not fixed; shown to fail on a deliberate change |
| security scanner | `scans-orderdesk` | injection traced end to end; a business-logic flaw found; inapplicable categories skipped; read-only |
| optimizer | `finds-report-bottleneck` | measured baseline; the real hot loop found, not the more complex decoy; algorithmic fix first |
| visualizer | `reports-partial-refactor` | done / partial / not-done told apart; moved complexity noticed; a quietly edited test assertion flagged |

## License

Apache License 2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE).
