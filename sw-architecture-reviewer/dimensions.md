# Improvement dimensions

What to look for in each dimension, with concrete patterns and anti-patterns. Use the function complexity table from the input docs as your primary hunting ground — high-LOC / high-complexity functions are usually where multiple dimensions fail at once, and the ones with high churn and no tests matter most. The table covers function-level problems; use the source code and runtime diagrams for the structure-level ones.

## 1. Simplicity

**Principle:** short, clean code; small single-purpose functions; no over-engineering for hypothetical futures.

**Look for:**
- Functions with LOC > ~50 or cyclomatic complexity > ~10 in the complexity table.
- Deep nesting (3+ levels of `if` / `for`).
- Abstraction layers with only one implementation ("interface" + one class).
- Configuration knobs that aren't read anywhere or always have the same value.
- "Manager" / "Helper" / "Util" classes that accumulate unrelated functions.
- Generic frameworks built in-house when a library or stdlib would do.
- Dead code paths and feature flags that have been "on" or "off" everywhere for months.

*Structure-level (from the source code and runtime diagrams):*
- Dependency cycles between packages/modules.
- Layer violations — arrows that skip a layer or point the wrong way (a handler importing a repository directly, a domain package importing the HTTP framework).
- A module everything depends on and that depends on everything (a "common" or "core" that became a hub).
- Two services reading and writing the same tables, so neither can change its schema alone.
- The same logic implemented separately in two components or two languages.

**Concrete improvements:**
- Break a dependency cycle by moving the shared piece down a layer or inverting one dependency behind an interface.
- Give shared data a single owning component; other components go through it.
- Split a fat function into named sub-functions along its natural seams.
- Inline a single-use abstraction.
- Delete unused configuration / feature flags.
- Replace a custom mini-framework with the standard library equivalent.

## 2. Testability

**Principle:** separation of concerns. Pure logic should be testable without I/O, network, time, or globals.

**Look for:**
- Functions that mix business logic with database calls, HTTP calls, file I/O, or system time.
- Static methods or singletons holding mutable state.
- Constructors that perform I/O or start background work.
- Direct use of `now()`, `random()`, environment variables, or filesystem inside business logic.
- Tests that require a full DB / network stack to assert a calculation.
- Modules with no tests at all in the complexity hotspots.

**Concrete improvements:**
- Extract pure functions (calculation, validation, formatting) from I/O-bearing functions.
- Inject dependencies via parameters or constructor args instead of importing globals.
- Pass a `Clock` / `RandomSource` / `Env` interface instead of calling them directly.
- Introduce a thin repository / gateway layer to isolate persistence.

## 3. Robustness

**Principle:** validate at boundaries, fail safely, survive long-running operation under load.

**Look for:**

*Input handling:*
- Endpoints / consumers that trust their input shape without validation.
- Missing length / range / type checks on user-supplied data.
- Raw stack traces or internal error messages leaked to end users.

*Failure handling:*
- Hard dependencies with no fallback (e.g., feature dies entirely if Redis is down).
- `catch` blocks that swallow errors silently.
- Retries without backoff or with no upper bound.
- No circuit breakers in front of flaky downstreams.
- Outbound calls (HTTP, DB, queue) with no timeout — one slow dependency stalls every caller.
- Retried or redelivered operations that aren't idempotent (a consumer that double-charges when a message is delivered twice).
- Dual writes with no atomicity: a sequence diagram that shows "write the DB, then publish the event" (or call a second service) loses or duplicates one side when the process dies in between.

*Long-running concerns:*
- Unbounded in-memory caches / queues / maps.
- Goroutines / threads / tasks started without lifecycle management or cancellation.
- Shared mutable state accessed from multiple goroutines/threads without synchronization (race conditions).
- Connections / file handles opened in hot paths without pooling or closing.
- Loops that load entire result sets into memory instead of streaming.

**Concrete improvements:**
- Add a validation layer at the HTTP / consumer boundary; reject early with a clear error.
- Introduce a fallback path (cached value, default, degraded mode) for non-critical dependencies.
- Bound caches with a size limit and eviction policy.
- Add cancellation contexts / timeouts to long-running operations.
- Make consumers and retried operations idempotent (idempotency key, upsert, dedup table).
- Replace a dual write with a transactional outbox, or make the second write recoverable.
- Replace shared mutable state with message passing, immutable copies, or explicit locks.

## 4. Observability

**Principle:** the runtime behavior of the system should be inspectable. Add traces and structured logging; use OpenTelemetry where possible; support a switchable debug mode.

**Look for:**
- Endpoints / jobs that emit no logs at all, or only `print` statements.
- Logs without correlation IDs / trace IDs / request IDs.
- No spans across service boundaries — can't follow a request from API to worker to DB.
- No metrics on latency, error rate, or throughput at component boundaries.
- Debug logging hardcoded on or off — no runtime toggle.
- Errors logged with `error: %v` and no context about the operation that failed.

**Concrete improvements:**
- Add OpenTelemetry spans at component boundaries (HTTP handlers, queue consumers, DB calls).
- Switch to structured logging (JSON) with consistent fields: `trace_id`, `request_id`, `user_id`, `component`.
- Add RED metrics (Rate, Errors, Duration) per endpoint or per consumer.
- Add a runtime-switchable log level (env var, signal handler, or admin endpoint).
- Add a `/debug` or `/health` endpoint exposing build info, config snapshot, dependency health.

---

# Benefit/risk/cost rubric

Score every proposed improvement on all three axes. State the assumption in one short clause.

## Benefit — how much real pain the change removes

| Level | When to assign |
|-------|----------------|
| **High** | Removes a failure mode that loses data, takes the service down, or goes unnoticed in production; or untangles a high-churn hotspot that most changes have to pass through; or unblocks testing of a core flow. |
| **Medium** | Makes a regularly-touched area noticeably easier to change, test, or debug; closes a failure mode that is contained or rare. |
| **Low** | Tidier, but in code that rarely changes and rarely fails. Nobody would notice next quarter. |

Anchor benefit in evidence from the docs and code — churn, complexity, missing tests, what the failure would cost — not in how unpleasant the code looks.

## Risk — chance the change breaks something currently working

| Level | When to assign |
|-------|----------------|
| **Low** | Additive change. New code path; existing code untouched or only renamed. Examples: adding a log line, adding a metric, extracting a pure function and calling it from the same place. |
| **Medium** | Modifies an existing code path that has test coverage (see the complexity map's Tests column), or touches a non-critical path. Examples: introducing a validation layer, adding retries, splitting a function. |
| **High** | Modifies a critical path with thin tests; changes data shapes; touches concurrency, persistence, or auth; coordinated changes across multiple services. Examples: introducing locking, changing a schema, refactoring an auth flow, replacing a framework. |

## Cost — engineering effort to implement and roll out

| Level | When to assign |
|-------|----------------|
| **Low** | One person, < 1 day. Localized to one file or module. No coordination. |
| **Medium** | One person, a few days to a week. Touches a handful of files or one subsystem. Some test additions. |
| **High** | Multi-week effort, or requires coordination across teams / services. Schema migration, framework swap, observability rollout across many services. |

## Quadrant guide for recommending

Benefit gates everything: a **Low benefit** item is deferred whatever its risk and cost, and listed as optional. For the rest:

- **Low risk + Low cost** → "quick wins", recommend first.
- **Low risk + High cost** → worth doing but plan it; good interns/onboarding work.
- **High risk + Low cost** → only do with explicit user sign-off and a clear rollback.
- **High risk + High cost** → flag as needing its own design doc before any work; consider whether it's really necessary.
