# software_architecture_skills

Five Claude Code skills that work as a pipeline for understanding, protecting, improving, optimizing, and verifying the architecture of an existing codebase.

## Skills

### `sw-architecture-writer`
Reverse-engineers a codebase and documents its architecture as ASCII diagrams plus a function complexity map. Produces four deliverables:

1. **Runtime architecture** — how components interact at runtime (HTTP, SQL, queues, etc.) with actors on the edges.
2. **Source code architecture** — package/module layout, one diagram per language, plus wiring artifacts (Dockerfile, compose, CI, IaC).
3. **Function complexity map** — table of non-trivial functions with file:line, LOC, cyclomatic complexity, and hotspot notes.
4. **Sequence diagrams** — important flows, with end users and external systems as actors.

### `sw-test-suite-generator`
Runs *after* the writer and ideally *before* the reviewer or optimizer: it turns the architecture docs into a **characterization test suite** — tests that pin the codebase's *current* behavior so any larger change that alters it trips an alarm. It's the safety net you put underneath a refactor, migration, or optimization before you start.

- **Cardinal rule** — tests never touch the real database or any production persistence. Every boundary the runtime diagram shows is isolated as either a **local test double** (in-memory fake/stub) or a **dedicated, throwaway test persistence** (Testcontainers, an ephemeral schema, an in-memory engine, or transactional rollback). The harness is **fail-closed**: it refuses to run against a non-test target rather than risk real data.
- **Flows from the docs** — the writer's **sequence diagrams** are the flow inventory, the **runtime diagram** is the boundary inventory, and the **complexity map** is the priority list (dense logic is what a refactor most likely breaks).
- **Characterization, not specification** — assertions encode what the system *actually does today*, bugs and all; the point is to detect *change*, including accidental "fixes". Suspected bugs are surfaced to the user, not silently corrected in an assertion.
- **Deterministic by construction** — frozen clock, seeded randomness, stabilized ordering, no real sleeps. A flaky net gets muted, and a muted net is no net.

It lets the user pick scope via selectable options (aimed at what upcoming changes will touch), generates the suite at the right pyramid level (unit tests for hotspots, integration tests for flows), then **runs it green and proves it touched no real persistence**, ending with a coverage map tying each test back to the flow or `file:line` it characterizes.

#### Example

Invoke it after the writer, pointing at the docs:

```
/sw-test-suite-generator   # then: "use the architecture docs in ./docs/architecture, I'm about to refactor the pricing module"
```

**1. It designs the isolation per boundary** (from the runtime diagram) before writing a line of test:

| Boundary | Treatment | Technique | How prod is kept safe |
|----------|-----------|-----------|-----------------------|
| postgres `orders` | dedicated test persistence | Testcontainers Postgres, schema dropped per run | DSN injected by fixture; harness refuses a non-`localhost` host |
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

...and proves isolation: the suite passes with the real `DATABASE_URL` unset, and the guard rejects a non-`localhost` DSN.

### `sw-architecture-reviewer`
Reads architecture documents (typically the writer's output) and proposes improvements across four dimensions:

- **Simplicity** — kill over-engineering, shrink fat functions, drop dead config.
- **Testability** — separate pure logic from I/O so it can be tested without a stack.
- **Robustness** — input validation, fallbacks, safe failure, memory/race-condition risks.
- **Observability** — OpenTelemetry traces, structured logging, switchable debug mode.

For each improvement it scores **risk** and **cost**, then lets the user select which to pursue. Only for the selected items it draws the future-state architecture (runtime, source code, sequence diagrams) and produces a phased implementation plan with validation and rollback per phase.

### `sw-performance-optimizer`
Analyzes the codebase together with its architecture documents to propose **concrete, measured** performance optimizations. It walks a strict priority ladder, cheapest-effective-fix first:

1. **Measure** — profile to find the real bottleneck (90% of time is usually in 5% of the code, and it's rarely the part you'd guess). Falls back to static analysis only when no profiler can run, and flags those findings as estimated.
2. **Algorithms & data structures** — the biggest wins: hash-map lookups over list scans, precomputed indexes over nested re-scans, the right container (heap / tree / set), memoization. An O(n²)→O(n log n) swap is ~50,000× at n=1,000,000.
3. **Architectural patterns** — caching, batching, concurrency/parallelism, precompute vs defer, not loading data you don't need, and database indexing.
4. **Hot code** — allocations, copies, cache locality, inside a proven-hot loop.
5. **Language/framework pushdowns** — moving a proven, isolated hot path to C/C++/Rust or a separate microservice, *with the risks each creates* spelled out (FFI/serialization overhead, build/deploy/debug complexity, memory safety, network hop, operational burden).

It scores each optimization by **impact / risk / cost**, lets the user pick, then produces a phased plan where every phase has a reproducible before/after **benchmark** and re-measures between phases (optimizations interact).

### `sw-refactor-visualizer`
Runs *after* the reviewer's improvements have been implemented, and visualizes the impact. For each implemented improvement it produces:

- A **before/after mermaid diagram** when the change was structural (split functions, moved modules, added validation/fallback/tracing steps) — skipped when there's no structural footprint.
- A **complexity-reduction table** comparing the affected functions before vs after, with explicit deltas, measured the same way as the baseline.
- A **verdict** on whether the improvement met its original goal.

It ends with a roll-up: aggregate complexity delta, a per-dimension scorecard, and outstanding debt for anything not implemented.

## Install

Symlink or copy each skill folder into a Claude Code skills directory.

Globally (available everywhere):
```bash
ln -s "$(pwd)/sw-architecture-writer"    ~/.claude/skills/
ln -s "$(pwd)/sw-test-suite-generator"   ~/.claude/skills/
ln -s "$(pwd)/sw-architecture-reviewer"  ~/.claude/skills/
ln -s "$(pwd)/sw-performance-optimizer"  ~/.claude/skills/
ln -s "$(pwd)/sw-refactor-visualizer"    ~/.claude/skills/
```

Project-scoped (checked into a specific repo):
```bash
ln -s "$(pwd)/sw-architecture-writer"    <your-project>/.claude/skills/
ln -s "$(pwd)/sw-test-suite-generator"   <your-project>/.claude/skills/
ln -s "$(pwd)/sw-architecture-reviewer"  <your-project>/.claude/skills/
ln -s "$(pwd)/sw-performance-optimizer"  <your-project>/.claude/skills/
ln -s "$(pwd)/sw-refactor-visualizer"    <your-project>/.claude/skills/
```

## Usage

The skills auto-trigger from their descriptions, or invoke manually:

```
/sw-architecture-writer
/sw-test-suite-generator
/sw-architecture-reviewer
/sw-performance-optimizer
/sw-refactor-visualizer
```

Typical pipeline: run the **writer** against an unfamiliar codebase; use the **test-suite-generator** to lay down a characterization safety net over the current behavior *before* changing anything; feed the writer's output to the **reviewer** to plan structural improvements (and/or to the **optimizer** to plan measured performance work); implement the selected ones — with the safety net catching any behavior that drifts; then run the **visualizer** to see the before/after impact and confirm complexity actually dropped. The **test-suite-generator** is what makes the bigger changes safe to make: it pins existing behavior so a refactor, migration, or optimization can't quietly regress it, and it does so without ever touching the real database. The **optimizer** is independent of the reviewer — reach for it whenever the goal is speed, latency, or resource cost rather than structure, using the writer's complexity map as its starting point.

## License

Apache License 2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE).
