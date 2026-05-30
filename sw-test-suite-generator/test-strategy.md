# Test strategy

The detail behind the skill: how to isolate every kind of persistence, how to keep the suite deterministic, which framework and conventions to match, and the self-review checklist. The throughline is the cardinal rule — **a test never touches real persistence** — and the secondary goal: a net that **alarms on behavioral change** without crying wolf.

---

## The characterization mindset

A characterization test (Michael Feathers' term; also "pinning test", "golden master") answers one question: *does the system still do what it did before this change?* It is not a specification of correct behavior — it is a snapshot of **actual** behavior.

Consequences that shape everything below:

- **Encode reality, not the ideal.** If the code rounds the wrong way, pin the wrong rounding. The test's value is detecting *change*, including a well-meaning "fix" nobody asked for. Flag suspected bugs to the user out-of-band; don't silently assert the corrected value.
- **Generate baselines from real runs.** You capture golden values by executing the (isolated) system, not by reasoning about what they should be. Eyeball each baseline once before committing it.
- **The alarm must be trustworthy.** A net that flakes gets muted; a muted net is no net. Determinism is not optional here — it is the feature.

---

## Persistence isolation

Every external boundary the runtime diagram shows gets exactly one of two treatments. Pick per boundary; never leave a real one wired in.

### The two treatments

- **Local test double** — in-memory/in-process fake, stub, or spy. No network, no disk. Fastest, most deterministic; best for unit tests and for boundaries whose contract you can fake faithfully.
- **Dedicated test persistence** — a real engine the test *owns and destroys*: a container, an ephemeral schema/db, an in-memory engine, or a transaction it rolls back. Higher fidelity (real SQL, real constraints); use when faking the engine would hide the behavior you're pinning.

### Techniques by boundary

| Boundary | Local double | Dedicated test persistence | Notes / trade-off |
|----------|--------------|----------------------------|-------------------|
| Relational DB (Postgres/MySQL) | repository fake backed by a dict/list; or SQLite/H2 in-memory | **Testcontainers** real engine; or ephemeral schema/db created+dropped per run; or open a txn per test and **roll back** | Fakes are fast but miss real SQL, constraints, and migrations. Prefer a container or rollback-per-test when the behavior depends on the engine. Rollback-per-test gives perfect isolation and speed when the schema already exists. |
| NoSQL / document store | in-memory map keyed like the store | Testcontainers (Mongo, etc.); or a throwaway namespace/collection | Match the consistency model you actually rely on. |
| Cache (Redis/Memcached) | `fakeredis`/in-memory map | Testcontainers Redis on an ephemeral db index | A cache double is usually enough; use a real one only when testing eviction/TTL behavior. |
| Message queue / broker (Kafka, SQS, Rabbit) | in-memory publisher/consumer capturing messages | Testcontainers broker; or an embedded broker | For *characterizing* what gets published, an in-memory capture you can assert on is usually better than a real broker. |
| Third-party HTTP API | stub/mock server returning **recorded fixtures**; VCR-style cassettes (`vcrpy`, `webmock`, WireMock, `nock`, `responses`) | — (never hit the real API) | Record once against the real API in a controlled setting, then replay offline. Scrub secrets from cassettes. Pin to the recorded response so contract drift trips the alarm. |
| Filesystem / object store | in-memory FS; temp dir the test creates and deletes (`tmp_path`, `t.TempDir()`) | MinIO/localstack via Testcontainers for S3-like APIs | Use the framework's temp-dir fixture; never write to a fixed real path. |
| **System clock** | inject a clock / freeze time (`freezegun`, `time-machine`, `Clock` interface, `jest.useFakeTimers`) | — | Time is persistence's quiet cousin: uncontrolled `now()` makes assertions nondeterministic. Always freeze. |
| **Randomness / UUIDs** | seed the RNG; inject an id generator | — | A test that asserts on a random UUID is flaky by construction. Seed or inject. |
| Environment / config | inject config; override env to test values | — | Read config through a seam so tests set test values; never depend on the developer's real env. |

### Guardrails — make it fail-closed

Convenience is how real databases get hit. Engineer it out:

- **Inject the target, don't discover it.** The test persistence DSN/URL/base-URL comes from the fixture, not from the same env var production reads. Tests should not be able to pick up a real connection string by accident.
- **Refuse non-test targets.** The harness asserts the target looks like a test one (host is `localhost`/container, db name carries a `test_` prefix, base URL points at the stub) and **aborts the run** otherwise. A missing test target is a hard failure, never a silent fallback to the default/real one.
- **No real client by default.** Construct clients to real boundaries only through the test seam. A test that builds a production client is the smell to catch in review.
- **Prove it (Step 6).** Run with real credentials/DSN unset and show the suite still passes; point the guard at a non-test host and show it refuses. State how you verified.

---

## The pyramid for a safety net

Lean on the cheap, fast, deterministic layers; use the expensive ones sparingly.

- **Unit tests (most of them).** Pin the **complexity-map hotspots** branch by branch — pure logic, no I/O, microseconds each. This is where dense logic that a refactor will disturb is cheapest to lock down. If logic is tangled with I/O and can't be unit-tested, that's a testability finding for [[sw-architecture-reviewer]].
- **Integration tests (some).** Pin cross-component **flows** from the sequence diagrams against the **dedicated test persistence** — real repository against a container/ephemeral schema, real serialization, real SQL. Slower; reserve for behavior the unit fakes can't faithfully reproduce.
- **End-to-end-ish (few).** A handful for the top user-facing sequences, driven through the real entry point with every boundary isolated. High value, high cost — keep the count low.

Map each test to the architecture artifact it came from: hotspot → unit test; sequence diagram → integration/e2e test.

---

## Determinism

A characterization suite must produce the same verdict every run or it gets ignored.

- **Freeze the clock.** No live `now()`/`Date.now()`/`time.time()` in asserted paths.
- **Seed randomness.** Fix the RNG seed; inject id/UUID generators.
- **Stabilize ordering.** Sort before asserting on collections the code leaves unordered (map iteration, query results without `ORDER BY`, concurrent appends).
- **No real waiting.** Replace `sleep`, real timeouts, and wall-clock retries with fake timers or injected schedulers.
- **Isolate state between tests.** Fresh fixture per test (rollback, truncate, or new container/schema). One test's writes must not leak into the next's reads.
- **No shared external state.** No reliance on test execution order, on a record "already being there", or on a developer's local config.

---

## Golden-master / snapshots

When output is large or structural (a rendered response, a serialized object graph, a generated file), snapshot it instead of hand-asserting every field.

- **Generate from a real, isolated run**, then **review the baseline once** before committing — an unreviewed snapshot pins whatever happened, including a bug you didn't notice.
- **Keep snapshots small and readable.** Trim volatile fields (timestamps, ids) by normalizing them before snapshotting, so the diff that trips the alarm is real behavior, not noise.
- **Re-blessing is a deliberate act.** Updating a snapshot should be a reviewed decision ("yes, this behavior changed on purpose"), not a reflexive `--update` on every red. That re-blessing moment *is* the alarm working.
- Tools: `syrupy`/`snapshottest` (Python), Jest snapshots (JS/TS), `approvaltests` (multi-language), `cupaloy`/golden files (Go), `insta` (Rust).

---

## Frameworks and conventions by language

Match what the repo already uses. If there's no existing setup, default to the idiomatic choice and say so.

| Language | Default framework | Isolation / fixture helpers |
|----------|-------------------|------------------------------|
| Python | `pytest` (or `unittest` if the repo uses it) | fixtures, `tmp_path`, `monkeypatch`; `testcontainers`, `freezegun`/`time-machine`, `responses`/`vcrpy`, `fakeredis` |
| Go | standard `testing` + table tests | `t.TempDir()`, `testcontainers-go`, `httptest`, interface seams for clocks/repos, golden files |
| Java / JVM | JUnit 5 (match 4 if that's the repo) | Testcontainers, `@TempDir`, WireMock, Mockito, H2 in-memory, a `Clock` bean |
| JS / TS | Jest or Vitest (match the repo) | `jest.useFakeTimers`, `nock`/`msw`, `testcontainers` (node), in-memory adapters |
| Ruby | RSpec or Minitest | `webmock`/VCR, `timecop`, database_cleaner / transactional fixtures |
| C# / .NET | xUnit (or NUnit/MSTest if used) | Testcontainers, `WireMock.Net`, in-memory EF provider (with care), an injected clock |

Cross-cutting conventions regardless of language:
- **Name for behavior**, not number: `test_expired_token_is_rejected`, not `test_auth_3`.
- **Arrange–act–assert**, one behavior per test.
- **Centralize the safe setup** (base fixture/conftest/test base class) so every test inherits isolation and none can opt out by accident.
- **Comment the link** to the flow or `file:line` being characterized, so a reader can trace a test back to the architecture docs.

---

## Self-review checklist

Run through this before handing the suite to the user.

### Isolation (the cardinal rule)
- [ ] Every boundary from the runtime diagram is treated as a local double **or** a dedicated test persistence — none left wired to a real target.
- [ ] The harness is **fail-closed**: it refuses to run against a non-test target and never silently falls back to the default/real one.
- [ ] Test targets are **injected** by fixtures, not discovered from the same config production reads.
- [ ] Isolation was **proven**, not asserted: ran with real credentials/DSN unset, and the guard rejects a non-test host. How it was verified is stated.

### Fidelity to current behavior
- [ ] Assertions encode **actual** captured behavior, generated from real isolated runs — not the idealized/should-be behavior.
- [ ] Suspected bugs are pinned as-is, commented, and surfaced to the user separately (not silently "fixed" in an assertion).
- [ ] Snapshots were reviewed once before committing; volatile fields are normalized; snapshots are small enough to read.

### Coverage that earns its keep
- [ ] Hotspot functions from the complexity map are pinned with unit tests, branch by branch.
- [ ] Important flows from the sequence diagrams are pinned with integration tests against the isolated persistence.
- [ ] Scope was chosen by the user via `AskUserQuestion`, aimed at what upcoming changes will touch — not a blind coverage-% grab.
- [ ] A coverage map ties each test back to the flow or `file:line` it characterizes.

### Determinism & quality
- [ ] Clock frozen, RNG seeded, unspecified ordering stabilized, no real sleeps/timeouts.
- [ ] State is isolated between tests (rollback/truncate/fresh container or schema); no order dependence.
- [ ] Tests are named for the behavior they pin and follow arrange–act–assert.
- [ ] The suite was **run and is green**; no assertion was weakened just to force a pass.

### Honesty
- [ ] Boundaries with no test seam are reported as blockers / testability findings for [[sw-architecture-reviewer]], not worked around by touching the real thing.
- [ ] Anything that couldn't be characterized (non-runnable path, missing representative data) is called out, not faked.
