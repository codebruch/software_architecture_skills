# Improvement dimensions

What to look for in each dimension, with concrete patterns and anti-patterns. Use the function complexity table from the input docs as your primary hunting ground — high-LOC / high-complexity functions are usually where multiple dimensions fail at once.

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

**Concrete improvements:**
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

# Risk/cost rubric

Score every proposed improvement with both axes. State the assumption in one short clause.

## Risk — chance the change breaks something currently working

| Level | When to assign |
|-------|----------------|
| **Low** | Additive change. New code path; existing code untouched or only renamed. Examples: adding a log line, adding a metric, extracting a pure function and calling it from the same place. |
| **Medium** | Modifies an existing code path that has test coverage, or touches a non-critical path. Examples: introducing a validation layer, adding retries, splitting a function. |
| **High** | Modifies a critical path with thin tests; changes data shapes; touches concurrency, persistence, or auth; coordinated changes across multiple services. Examples: introducing locking, changing a schema, refactoring an auth flow, replacing a framework. |

## Cost — engineering effort to implement and roll out

| Level | When to assign |
|-------|----------------|
| **Low** | One person, < 1 day. Localized to one file or module. No coordination. |
| **Medium** | One person, a few days to a week. Touches a handful of files or one subsystem. Some test additions. |
| **High** | Multi-week effort, or requires coordination across teams / services. Schema migration, framework swap, observability rollout across many services. |

## Quadrant guide for recommending

- **Low risk + Low cost** → "quick wins", recommend first.
- **Low risk + High cost** → worth doing but plan it; good interns/onboarding work.
- **High risk + Low cost** → only do with explicit user sign-off and a clear rollback.
- **High risk + High cost** → flag as needing its own design doc before any work; consider whether it's really necessary.
