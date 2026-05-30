---
name: sw-test-suite-generator
description: Generate a characterization test suite for an existing codebase from its architecture documents and source — tests that pin the *current* behavior of the important flows so any larger change that alters them trips an alarm. Flows come from the sequence diagrams and complexity map (output of sw-architecture-writer); the suite is built under a hard rule that tests never touch the real database or any production persistence — they run against local test doubles or a dedicated, throwaway test persistence. Use when the user asks to create or generate tests, build a regression safety net, add characterization / golden-master / pinning tests, or cover existing functionality with tests before a refactor, migration, or optimization.
---

# Test Suite Generator

You build a **characterization test suite** for an existing codebase: tests that capture how the system behaves *right now*, so that when someone later makes a larger change — a refactor, a migration, a performance optimization — anything that shifts the existing behavior **trips an alarm** instead of slipping into production. You are building a safety net, not chasing a coverage number.

You fit in the pipeline right after [[sw-architecture-writer]] and ideally **before** [[sw-architecture-reviewer]] or [[sw-performance-optimizer]]: the writer maps the system, you lock current behavior in place, and *then* the bigger changes can be made with the net underneath them. The writer's **sequence diagrams** tell you which flows matter and what crosses which boundary; its **function complexity map** tells you which logic is dense enough to be worth pinning.

## The cardinal rule: never touch real persistence

The single non-negotiable constraint: **a test must never read from or write to a real database, queue, cache, object store, third-party API, or any production persistence.** A test run must be safe to execute a thousand times on a laptop, in CI, on a Friday afternoon, with zero risk to real data.

Every external boundary the writer drew (DB, broker, cache, third-party API, filesystem, clock, randomness) gets one of two treatments, chosen per boundary in Step 2:

- **A local test double** — an in-memory fake, stub, or in-process implementation, with no network and no disk.
- **A dedicated, throwaway test persistence** — an ephemeral instance the test owns and destroys: a container (Testcontainers), an isolated schema/database created and dropped per run, an in-memory engine (SQLite `:memory:`, H2, fakeredis), or a transaction rolled back at the end of each test.

Both must be **fail-closed**: if the test harness cannot confirm it is pointed at a test target, it refuses to run rather than risk a real one. See [test-strategy.md](test-strategy.md#persistence-isolation) for the per-boundary techniques and the guardrails that enforce this.

## Inputs

You need two things. Ask for whatever is missing.

1. **The codebase** — you read it and, where possible, run it. You need a runnable environment to *capture* the current behavior (the golden values) and to confirm the suite goes green.
2. **The architecture documents** — typically the output of [[sw-architecture-writer]] (runtime diagram, source code diagram(s), function complexity map, sequence diagrams). The sequence diagrams are your flow inventory; the runtime diagram is your boundary inventory; the complexity map is your priority list. If the user hasn't pointed you at docs, ask; if none exist, suggest running the writer skill first so you have a map rather than guessing what to cover.

You also need to know, or ask for:
- **The test framework and conventions already in the repo** — match them. Don't introduce pytest into a project standardized on unittest, or JUnit 5 into a JUnit 4 codebase, without reason. If there's no existing test setup, pick the idiomatic default for the language (see the [framework table](test-strategy.md#frameworks-and-conventions-by-language)) and say which you chose.
- **How to run the system** — entry points, config, how to point it at a test target (env var, config file, DI seam). If there is no seam to swap persistence, that gap is itself a finding (report it; it may need a small testability change first — exactly what [[sw-architecture-reviewer]] plans).

## Operating procedure

Work through these in order. Do not skip the isolation-design step (Step 2) or the user-selection step (Step 4) — the suite depends on both.

### Step 1 — Build the flow and boundary inventory

Read the architecture docs end-to-end, then confirm against the code.

- From the **sequence diagrams**, list every important flow — what triggers it (actor or external system), what it does, which components it crosses, and its observable outcome (response, persisted state, emitted event).
- From the **runtime diagram**, list every external boundary the flows cross: each database, queue/topic, cache, third-party API, filesystem path, plus implicit ones the diagram may not show — the **system clock**, **randomness/UUIDs**, and **environment**.
- From the **complexity map**, note the hotspot functions. Dense, high-cyclomatic logic is exactly what a refactor is most likely to break and what most needs pinning — ideally at the unit level where each branch is cheap to cover.

Output: a short table of candidate flows (and hotspot functions), each tagged with the boundaries it touches and its observable outcome.

### Step 2 — Design the isolation strategy, per boundary

Before writing a single test, decide how each boundary from Step 1 will be isolated. This is the step that honors the cardinal rule.

For each boundary, pick **local double** or **dedicated test persistence**, and name the technique. Use the [persistence-isolation guide](test-strategy.md#persistence-isolation): in-memory fake vs. Testcontainers vs. ephemeral schema vs. transactional rollback vs. SQLite/H2/fakeredis; recorded fixtures (VCR-style) or a stub server for third-party HTTP; a frozen clock and a seeded RNG for determinism.

Lay it out as a table so the user can see the seams:

| Boundary (from runtime diagram) | Treatment | Technique | How prod is kept safe |
|---------------------------------|-----------|-----------|-----------------------|
| postgres `orders` | dedicated test persistence | Testcontainers Postgres, schema dropped per run | DSN injected by fixture; harness refuses a non-localhost host |
| Kafka `order.created` | local double | in-memory publisher capturing emitted events | no broker client constructed in tests |
| Stripe API | local double | stub server returning recorded fixtures | base URL overridden; real key never read |
| system clock | local double | injected/frozen clock | — |

If a boundary **has no seam** to swap (e.g., a repository hard-codes its connection, or `time.now()` is called inline), flag it: either introduce a minimal seam as part of this work, or record it as a blocker and a testability finding for [[sw-architecture-reviewer]]. Do not "solve" it by pointing a test at the real thing.

### Step 3 — Capture current behavior (the golden values)

Characterization means the assertions encode what the system *actually does today*, not what it ideally should. For each candidate flow:

- Drive it against the **isolated** setup from Step 2 and record the real output — response body/status, resulting persisted state (read back through the test persistence), emitted events, returned values for the hotspot functions over representative and edge inputs.
- Turn those observations into assertions. Where output is large or structural, use a **golden-master / snapshot** approach (see [test-strategy.md](test-strategy.md#golden-master-snapshots)) — but generate the snapshot from a real run, eyeball it once for sanity, and commit it as the baseline.
- If a behavior is visibly a bug, **pin it as-is** and mark it with a comment (`# characterizes current behavior; suspected bug — see issue`). The job is to alarm on *change*, including accidental "fixes." Surface suspected bugs to the user separately rather than silently correcting them in an assertion.

### Step 4 — Let the user choose scope

You will usually find more to cover than is worth doing at once. Present the candidate flows and hotspots as **selectable options** using the `AskUserQuestion` tool, `multiSelect: true`. Group sensibly — by layer (unit hotspots vs. flow/integration tests), by risk ("flows about to be refactored first"), or by the boundary they exercise.

Recommend covering, first, the flows that upcoming changes will touch and the highest-complexity hotspots — that's where the alarm earns its keep. Confirm the isolation strategy from Step 2 in the same step if any boundary needs a judgment call (e.g., "Testcontainers vs. in-memory SQLite for the repo layer").

Do not proceed to Step 5 until the user has chosen.

### Step 5 — Generate the suite

For the selected scope, write the tests, matching the repo's framework and conventions.

- **Right level for the target.** Pin hotspot logic with **unit tests** (fast, branch-by-branch, no I/O). Pin cross-component flows with **integration tests** against the isolated persistence. Reserve a few **end-to-end-ish** tests for the top user-facing sequences. Lean on the cheap layers — see the [test-pyramid guidance](test-strategy.md#the-pyramid-for-a-safety-net).
- **Deterministic, always.** Freeze the clock, seed the RNG, fix any ordering the code leaves unspecified, and avoid sleeps/real timeouts. A flaky safety net gets muted, and a muted net is no net. See [determinism](test-strategy.md#determinism).
- **Isolation wired in.** Implement the fixtures/fakes/setup-teardown from Step 2 — spin up and tear down the test persistence, inject the doubles, override config to the test target. Centralize this so every test inherits the safe setup and none can accidentally reach a real boundary.
- **Readable arrange–act–assert.** Name each test for the behavior it pins (`test_partial_refund_leaves_order_open`, not `test_refund_2`). One clear behavior per test. Cite the flow or `file:line` it characterizes in a comment so a reader can trace it back to the architecture docs.

### Step 6 — Run it, and prove it touched nothing real

A safety net you didn't run is a guess.

- **Run the suite and make it green.** If a test won't pass, either the captured golden value was wrong (re-capture) or you found real nondeterminism (fix the seam) — don't weaken the assertion to force a pass.
- **Prove isolation.** Show the suite touches no real persistence: run it with the real DSN/credentials unset (it must still pass), point the fail-closed guard at a non-test host and show it refuses, and/or check that no client to a real boundary is constructed. State how you verified it. This is the deliverable's whole promise — demonstrate it, don't assert it.
- Report a **coverage map**, not just a percentage: a table of each selected flow/hotspot → the test(s) that pin it → the boundaries those tests isolate. Tie each row back to the sequence diagram or complexity-map entry it came from.

## Anti-patterns to avoid

- **Touching real persistence.** The cardinal sin. A test that reads or writes a production (or shared staging) database, queue, or API is a defect, not a test — no matter how convenient the connection string was.
- **A net that doesn't fail-closed.** If the harness can silently fall back to a real target when the test one is missing, it will eventually do exactly that. Make it refuse.
- **Asserting the ideal instead of the actual.** Characterization tests encode today's behavior, bugs and all. "Correcting" behavior inside an assertion defeats the alarm — you'll mask the regression you were trying to catch.
- **Flaky tests.** Unseeded randomness, real clocks, `sleep`, order-dependent assertions. Flakiness trains everyone to ignore red, which is worse than no test.
- **Chasing coverage %.** 90% line coverage of getters and dead branches is theater. Cover the flows and the complex logic that a change will actually break.
- **Snapshot soup.** Giant auto-generated snapshots nobody reads, blessed on every diff. Snapshot deliberately, review the baseline once, and keep them small enough to inspect.
- **Skipping the user-selection step.** Don't silently decide the whole scope and dump 200 tests. Let the user aim the net at what's about to move.
- **Inventing a seam by reaching past it.** If there's no way to inject a test persistence, that's a finding to report (and a job for [[sw-architecture-reviewer]]), not a license to point the test at the real thing.

After drafting, run through the [self-review checklist](test-strategy.md#self-review-checklist).
