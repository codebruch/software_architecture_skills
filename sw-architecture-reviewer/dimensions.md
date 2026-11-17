# Improvement dimensions

What to look for in each dimension, with concrete patterns and anti-patterns. Use the function complexity table from the input docs as your primary hunting ground — high-LOC / high-complexity functions are usually where multiple dimensions fail at once, and the ones with high churn and no tests matter most. The table covers function-level problems; use the source code and runtime diagrams for the structure-level ones.

## Principles explain findings; they are not findings

The patterns below come from familiar design principles — coupling and cohesion, single responsibility, KISS and YAGNI, DRY, encapsulation, dependency inversion, fail-fast — and from the named anti-patterns (god object, leaky abstraction, static cling, big ball of mud). Use them to know where to look. Do not report them.

"`OrderService` violates the single-responsibility principle" tells the user nothing they can weigh. "`OrderService` is imported by 14 modules and was changed in 31 of the last 50 commits, for pricing, shipping, and email reasons alike; pricing changes keep breaking shipping tests" is a finding: it names a cost, shows the evidence, and makes the benefit of fixing it scorable. If you can't state the cost a pattern is causing *in this codebase*, leave it out.

Three cautions, because principles applied by rote do damage:

- **They pull against each other.** DRY raises coupling. Seams for testability add indirection that simplicity counts against. Fallbacks for robustness hide errors that fail-fast would surface. When a proposal helps one dimension at another's expense, say so in its Reasoning and let the scores carry the trade.
- **Proportion.** Layers, repositories, ports and adapters, and interfaces earn their keep in large, long-lived, much-changed code. A 600-line service with three tables does not need a domain layer that is ignorant of persistence. Match the proposal to the size of the system and to how often the area changes (the Churn column).
- **Open/closed, interface segregation, and dependency inversion are the principles most often used to justify speculative abstraction** — the interface with one implementation that the Simplicity section tells you to remove. Recommend an extension point only where history shows the same code being edited again and again to add variants; recommend splitting an interface only where implementers stub out methods they don't need.

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
- The same **business rule** implemented in two places that must change together (a tax rate in the API and again in the report job). The test is "if the rule changed, would both have to change?" — not whether the text looks alike. Code that merely resembles other code is not a finding; merging it couples two things that were free to diverge, and a wrong shared abstraction costs more than the duplication did.
- **God module or class**: many unrelated functions, many dependents, touched by most commits whatever their purpose. The function-level complexity map can miss it — each function may be small. Look at fan-in on the source diagram and at churn.
- **Shotgun changes**: one logical change routinely edits the same set of files together (`git log --name-only` shows the pairs). The files are one unit that was split along the wrong line, or a rule is duplicated across them.
- **Cross-cutting concerns copied inline**: authentication, authorization, validation, transactions, error mapping, or logging written out in each handler instead of applied in one place (middleware, decorator, pipeline). Every copy is a chance to forget one — check whether one already has been.
- **Leaky abstractions**: a layer that exposes what it was meant to hide — database rows or ORM entities returned straight through the API, a vendor SDK's types and error codes in business logic, SQL fragments passed down from handlers. The cost is that a schema or vendor change becomes an API change.
- **State without an owner**: a status field or invariant written from many places (the order status set by string assignment in four functions), so no single piece of code can guarantee it stays valid.
- **Inheritance used for reuse**: deep hierarchies, or base classes whose subclasses override most of it or call up and down to get anything done.
- **No discernible structure at all** (the "big ball of mud"): that is a description, not an improvement. Never answer it with "re-architect" or "rewrite". Find the one or two seams where a boundary would pay off soonest — usually around the highest-churn area — and propose those as incremental steps.

**Concrete improvements:**
- Break a dependency cycle by moving the shared piece down a layer or inverting one dependency behind an interface.
- Move a cross-cutting check to a single enforcement point that applies by default.
- Map at the boundary: return a response shape the API owns, not the storage row.
- Give a status or invariant one owner; other code asks it to make the change.
- Give shared data a single owning component; other components go through it.
- Split a fat function into named sub-functions along its natural seams.
- Inline a single-use abstraction.
- Delete unused configuration / feature flags.
- Replace a custom mini-framework with the standard library equivalent.

## 2. Testability

**Principle:** separation of concerns. Pure logic should be testable without I/O, network, time, or globals.

**Look for:**
- Functions that mix business logic with database calls, HTTP calls, file I/O, or system time.
- Static methods, singletons, or module-level globals that hold mutable state or perform I/O ("static cling"). A static *pure* function is fine and needs no seam — the problem is hidden state and hidden I/O, not the keyword.
- Functions that answer a question *and* change state — a getter that also writes a cache, a "check" that also sends a notification. Callers can't use the answer without triggering the effect, and tests must account for both.
- Objects handed around half-filled: one type whose fields are populated differently depending on which path built it, so every consumer must guess what is set. Tests need a different fixture per path, and production gets null errors.
- Constructors that perform I/O or start background work.
- Direct use of `now()`, `random()`, environment variables, or filesystem inside business logic.
- Tests that require a full DB / network stack to assert a calculation.
- Modules with no tests at all in the complexity hotspots.

**Concrete improvements:**
- Extract pure functions (calculation, validation, formatting) from I/O-bearing functions.
- Inject dependencies via parameters or constructor args instead of importing globals.
- Pass a `Clock` / `RandomSource` / `Env` interface instead of calling them directly.
- Introduce a thin repository / gateway layer to isolate persistence — where logic worth testing is tangled with queries. Don't wrap straightforward CRUD in a layer that only forwards calls.
- Separate the question from the action, so the pure part can be tested alone.
- Replace a partially-populated object with distinct types for distinct shapes, or load the whole thing.

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

*Failing fast versus degrading — pick per case, deliberately:*
- **Fail fast** on what should never happen: invalid configuration, a missing required setting, a broken invariant, a programmer error. Look for services that start with bad config and fail on the first request an hour later, defaults silently substituted for required values, and code that carries on after detecting an impossible state.
- **Degrade** on what is expected to happen: a slow or unavailable external dependency that the feature can live without for a while.
- Either way, **never silently**. A fallback that is not logged and counted hides an outage until the fallback itself fails. Look for fallbacks and default values with no log line or metric beside them.
- Proposals to add a fallback must say what stale or default data costs the user; if the answer is "wrong money" or "wrong permissions", fail instead.

*Consistency across a network boundary* (only where data lives in more than one place — a cache, a replica, a second service, a queue):
- Code that reads its own write back from a replica or cache and assumes it is there.
- No stated answer to "when the other side is unreachable, do we refuse the request or serve what we have?" — each call site has chosen by accident.
- Cached data with no expiry or invalidation path, on a value whose staleness matters.

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

## 5. Security

**Principle:** nothing from outside a trust boundary is believed or obeyed until it has been authenticated, authorized, and validated; every component holds the least privilege and the fewest secrets it can work with.

Find the trust boundaries first. On the runtime diagram, every arrow that starts at an actor (end user, admin, operator) or an external system crosses one; so does every arrow between components that run with different privileges or belong to different tenants. Walk each boundary and ask the questions below. This overlaps with Robustness on input validation — robustness asks "does bad input fail safely?", security asks "what can someone who *wants* to break it do?".

**Look for:**

*Authentication and authorization:*
- Entry points (routes, consumers, admin/debug endpoints, scheduled-job triggers) reachable with no authentication, or behind a check that lives only in the UI or the gateway.
- Authorization that checks "is logged in" but not "may act on *this* object" — handlers that load a record by an id from the request without checking ownership or tenant.
- Authorization scattered inline through handlers instead of enforced at one layer, so each new endpoint has to remember it.
- Internal service-to-service calls that trust any caller on the network.
- Home-grown session, token, password-hashing, or crypto code where a vetted library exists.

*Untrusted input reaching an interpreter:*
- SQL, shell commands, templates, file paths, URLs for outbound requests, or deserializers built from request data by string concatenation or passed through unchecked (injection, path traversal, server-side request forgery, unsafe deserialization).
- File uploads stored or served without type, size, and location constraints.
- Messages from a queue or webhook treated as trusted because they arrive "from inside" — check where they originate and whether the signature is verified.

*Secrets and credentials:*
- Secrets in source, config files, Dockerfiles, CI definitions, or IaC committed to the repo; default or shared credentials.
- One credential shared by every component, or an application database user with owner/superuser rights.
- Secrets, tokens, or personal data written to logs, traces, error messages, or metrics labels.
- No way to rotate a secret without a redeploy or downtime.

*Data protection:*
- Sensitive data (credentials, personal data, payment data) crossing a boundary in plaintext, or stored unencrypted where the threat model expects encryption.
- Responses that return whole internal records when the caller needs three fields.
- No tenant isolation in the data layer of a multi-tenant system — the tenant filter is each query's responsibility.

*Exposure and containment:*
- Debug, metrics, health, or admin endpoints listening on the public interface.
- No rate limiting or lockout on login, password reset, or other costly/abusable endpoints.
- A component that, if compromised, can reach everything (flat network, broad IAM role, container running as root).
- Security-relevant actions (login, permission change, data export, admin operations) leaving no audit record.
- Dependencies or base images pinned to versions with known vulnerabilities, or not pinned at all — note it and recommend a dependency audit rather than attempting one here.

**Concrete improvements:**
- Enforce authentication and authorization in one place (middleware, a policy layer, a gateway *plus* a service-side check) that every entry point passes through by default.
- Add object-level and tenant-level checks in the service or repository layer, where they can't be skipped.
- Replace string-built queries/commands with parameterized queries and argument arrays; allow-list paths and outbound hosts.
- Move secrets to a secret manager or injected environment; give each component its own least-privilege credential; scrub secrets and personal data from logs.
- Verify signatures on webhooks and inter-service messages; use mutual TLS or signed tokens between services.
- Bind debug/admin endpoints to an internal interface or put them behind authentication; add rate limits to authentication flows.
- Add an audit log for security-relevant actions (ties in with Observability).

**Handling what you find:**
- Cite the location of a secret or a hole (`file:line`); never copy a secret's value or write a working exploit into the findings or the saved review.
- A credential found in the repo is compromised whether or not the code is fixed — the improvement includes rotating it, and it stays in git history until rewritten.
- A confirmed, externally exploitable finding is raised with the user immediately rather than left as one row among twenty.

---

# Benefit/risk/cost rubric

Score every proposed improvement on all three axes. State the assumption in one short clause.

## Benefit — how much real pain the change removes

| Level | When to assign |
|-------|----------------|
| **High** | Removes a failure mode that loses data, takes the service down, or goes unnoticed in production; or closes a hole an untrusted actor can reach (missing authentication or authorization, injection, an exposed secret); or untangles a high-churn hotspot that most changes have to pass through; or unblocks testing of a core flow. |
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

Security changes need one more check when scoring risk: tightening authentication, authorization, or validation *is meant* to reject requests that used to succeed, so legitimate callers relying on the loose behavior will break. Plan those with a log-only or report-only stage first where the system allows it, then enforce.
