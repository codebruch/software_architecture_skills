# Optimization ladder

The detail behind each rung of the priority ladder, with concrete patterns, tooling, and rubrics. The order is the point: **the wins shrink and the costs grow as you go down.** Don't descend a rung until the one above is exhausted on the path you're optimizing.

---

## Rung 1 — Measure to find the real bottleneck

You cannot optimize what you haven't measured. Two facts drive everything below:

- **The 90/5 rule.** Roughly 90% of the runtime is spent in ~5% of the code, and that hot spot is rarely the one you'd have guessed. Intuition is wrong often enough that betting engineering effort on it is a bad trade.
- **Amdahl's law.** The most you can speed up the whole program is bounded by the fraction of time the part you optimize actually consumes. A 100× speedup on code that's 2% of runtime caps out at a ~2% overall win. Always check the profiler share before investing.

### Profilers by language

Pick the tool that matches the runtime, run it against a **representative workload**, and read it as a flame graph or a top-N-by-self-time list.

| Language / runtime | Tools | Notes |
|--------------------|-------|-------|
| C / C++ / Rust / native | `perf`, `valgrind --tool=callgrind`, `cargo flamegraph`, Instruments, VTune | `perf record`/`perf report` for CPU; callgrind for instruction-level; sanitizers/`heaptrack` for memory |
| Python | `py-spy` (sampling, no code change), `cProfile` + `snakeviz`, `scalene` (CPU+mem), `memray` | `py-spy top` / `py-spy record` on a live process is the fastest start |
| Go | `pprof` (CPU, heap, mutex, block), `go test -bench` + `-benchmem`, `trace` | built-in; `net/http/pprof` exposes live profiles |
| Java / JVM | `async-profiler`, JFR (Flight Recorder), VisualVM, `jmh` for microbenchmarks | async-profiler gives mixed Java+native flame graphs |
| Node / JS / TS | Chrome DevTools Performance + Memory tabs, `--prof`/`--cpu-prof`, `clinic.js`, `0x` | DevTools flame chart for front-end and Node |
| Browser / front-end | Chrome DevTools (Performance, Lighthouse, Coverage), WebPageTest | profile Core Web Vitals (LCP/INP/CLS), not just JS CPU |
| Ruby | `stackprof`, `rbspy`, `ruby-prof` | `rbspy` samples a live process like py-spy |
| .NET | `dotnet-trace`, `dotnet-counters`, PerfView, Visual Studio Profiler | |
| Databases | `EXPLAIN ANALYZE`, slow-query log, `pg_stat_statements`, `auto_explain` | the DB is often *the* bottleneck — profile queries, not just app code |

If none of these can be run (no environment, no representative data, no way to drive load), fall back to static reasoning over the architecture's sequence diagrams and complexity map — and **label every estimate as such.** A static guess is a hypothesis to confirm with a profiler, not a result.

### What to capture

- A **baseline number** for the goal metric: p50/p99 latency, throughput (req/s, rows/s), CPU time, peak RSS, allocation rate, or cloud cost — whichever the user is optimizing.
- A **ranked bottleneck list**: "X% of wall time / CPU / allocations in `file:func`", sorted by cost, each tagged with how it was obtained.
- The **workload** used, so the measurement is reproducible and the after-numbers are comparable.

---

## Rung 2 — Algorithms & data structures

The biggest wins live here, because complexity class dominates everything at scale. Replacing an **O(n²)** algorithm with **O(n log n)** is a ~2× win at n=20, but at n=1,000,000 it's roughly **50,000×** — no amount of hot-loop tuning or language rewrite competes with that. Fix the complexity class before anything below it.

### Patterns

- **Hash map instead of list scan.** Checking membership by scanning a list is O(n) per check, O(n²) in a loop. A hash map/set makes it O(1) per check. Classic "this report takes 40 minutes" culprit.
- **Precompute an index / lookup table.** Nested loops that re-scan the same data to correlate it are O(n·m). Build a map keyed by the join field once (O(n+m)), then look up.
- **Pick the container for the access pattern:**
  - **Hash set/map** — membership, dedup, keyed lookup → O(1).
  - **Heap / priority queue** — "give me the smallest/largest repeatedly" → O(log n) per pop instead of O(n) re-scan.
  - **Balanced tree / sorted structure** — range queries, ordered iteration, nearest-key → O(log n).
  - **Array / contiguous buffer** — index access and tight iteration (also best for rung-4 cache locality).
  - **Trie / bitset / Bloom filter** — prefix matching, dense integer sets, probabilistic membership.
- **Memoize / cache recomputed results.** A pure expensive function called repeatedly with the same arguments inside a loop should be memoized. (When the result is shared across requests/processes, that's caching — rung 3.)
- **Lazy evaluation / short-circuit.** Don't compute what you don't consume. Stream, paginate, or generate on demand instead of materializing whole collections.

The signal: look at the **complexity-map hotspots** and the **call frequency**. A modest-complexity function called a million times beats a complex one called twice.

---

## Rung 3 — Architectural patterns

When the algorithm is already right but the *shape and placement of the work* is wrong. These are about I/O, where data lives, and how work is scheduled.

- **Caching.** Store results so you don't recompute or re-fetch. Layers, cheapest first: in-process memory → shared cache (Redis/Memcached) → HTTP caching (`Cache-Control`, ETags) → CDN at the edge. The hard part is **invalidation and staleness** — define the TTL/eviction and what stale data costs before adding it.
- **Batching.** Replace one-item-at-a-time round trips with one bulk operation: `SELECT ... WHERE id IN (...)` instead of N queries (the **N+1 query** problem), bulk insert/`COPY`, batched API calls, vectorized array ops. Trades latency for throughput; mind the batch size.
- **Concurrency / parallelism.** Do independent work simultaneously — **async I/O** for I/O-bound waits, **threads/goroutines** for in-process parallelism, **processes/machines** for CPU-bound or scale-out. Only helps when work is genuinely independent; adds risk of races, deadlocks, and nondeterminism (higher risk score).
- **Precompute vs defer.** Do work ahead of time when the input is known (materialized views, precomputed aggregates, build-time generation), or defer it until actually needed (lazy init, on-demand computation). Pick based on read/write ratio.
- **Don't move data you don't need.** Paginate, project only the columns you use (`SELECT col` not `SELECT *`), filter at the source (predicate pushdown), stream large result sets instead of loading them into memory.
- **Database tuning.** Indexes are the "right data structure" idea applied to the DB — a missing index turns minutes into milliseconds. Use `EXPLAIN ANALYZE` to find seq scans on large tables, add covering/composite indexes for the actual query shape, fix N+1s, and watch connection-pool limits. Often the single highest-impact rung-3 lever in a data-heavy app.

---

## Rung 4 — Hot-code micro-optimization

Only inside a loop the profiler has **proven** is hot, and only after rungs 2–3 are settled. The wins are percentages, not orders of magnitude.

- **Allocations.** Reuse buffers/objects, pool them, preallocate to known capacity, avoid per-iteration allocation. In GC languages this also cuts collection pressure.
- **Copies.** Pass by reference/pointer/slice/view instead of copying; avoid defensive copies in the hot path; use zero-copy I/O where the runtime supports it.
- **Cache locality.** Iterate contiguous memory in order; prefer struct-of-arrays for column-wise access; keep hot fields together; avoid pointer-chasing data structures in the inner loop.
- **Hoist invariants** out of the loop; strength-reduce; let the compiler vectorize (or do it explicitly only with a benchmark proving it helps).

Measure each change individually — micro-optimizations frequently do nothing (or regress) because the bottleneck was elsewhere, the compiler already did it, or memory latency dominates.

---

## Rung 5 — Language/framework pushdowns

The last resort: move a **proven, isolated, irreducible** hot path to a faster language (C, C++, Rust) via FFI/native extension, or split it into a separate microservice. Expensive and risky — justified only when rungs 2–4 are exhausted on a path the profiler shows dominates runtime.

### When it can be worth it

- A tight CPU-bound kernel (numeric, parsing, compression, crypto) that's already algorithmically optimal and still dominates.
- A path with a clean, narrow interface and large work per call (so call/serialization overhead is amortized).
- A need that the host language structurally can't meet (true parallelism under a GIL, manual memory layout, SIMD).

### Risks to state every time

**Native-language pushdown (C/C++/Rust extension):**
- **FFI / boundary overhead** — crossing the language boundary has per-call cost; a chatty interface can erase the speedup. Push down coarse-grained work, not a function called a million times in a loop.
- **Serialization / marshalling** — converting data across the boundary (and copying it) can cost more than the computation saved.
- **Memory safety** — C/C++ reintroduce segfaults, buffer overflows, and use-after-free that crash the whole host process; Rust mitigates this but adds a learning curve.
- **Build & deploy complexity** — a toolchain, cross-compilation, platform-specific binaries, and ABI compatibility now stand between a commit and a release.
- **Debugging & observability** — stack traces, profilers, and error handling no longer span the boundary cleanly; crashes are harder to diagnose.
- **Team skills & maintenance** — fewer people can safely change it; it becomes a bus-factor and onboarding cost.

**Microservice extraction (separate process/service):**
- **Network hop** — a function call becomes an RPC: added latency, timeouts, retries, partial failure, and back-pressure to handle.
- **Serialization** at the wire boundary on every call.
- **Operational burden** — another deployable to build, deploy, monitor, scale, secure, and page someone for.
- **Data consistency / coupling** — distributed state, versioned contracts, and the need to keep the two sides compatible across deploys.

Rule of thumb: a pushdown should make the path **≥10×** faster on a segment that's a **large share** of runtime, with an interface coarse enough that boundary cost is noise. If it can't clear that bar, stay on a higher rung.

---

## Impact/risk/cost rubric

Score every proposed optimization on all three axes. State the assumption in one short clause, and say when impact is estimated rather than measured.

### Impact — expected improvement on the goal metric

| Level | When to assign |
|-------|----------------|
| **High** | Changes the complexity class on a dominant bottleneck (O(n²)→O(n log n) at large n), removes a top profiler entry, or cuts the goal metric by a large factor. Most rung-2 fixes and high-leverage rung-3 (missing index, killing an N+1). |
| **Medium** | Meaningful but bounded — a solid constant-factor win, caching/batching on a moderate path, parallelizing a secondary stage. |
| **Low** | Small percentage win, or a win on a path that's a small share of runtime (Amdahl-capped). Most rung-4 micro-optimizations land here unless the loop is genuinely dominant. |

Anchor impact to the profiler share: an optimization can't beat the fraction of runtime its target consumes.

### Risk — chance the change breaks correctness or behavior

| Level | When to assign |
|-------|----------------|
| **Low** | Behavior-preserving and well-covered: swap a data structure behind a stable interface, add an index, memoize a pure function. |
| **Medium** | Changes a code path with thinner coverage, or alters ordering/timing: batching, lazy loading, single-threaded restructuring. |
| **High** | Concurrency/parallelism (races, deadlocks, nondeterminism), cache invalidation (staleness/correctness), schema changes, or any rung-5 pushdown (process boundary, memory safety, distributed failure). |

### Cost — engineering effort to implement, benchmark, and roll out

| Level | When to assign |
|-------|----------------|
| **Low** | One person, < 1 day, localized to one function/module. Most rung-2 swaps and index additions. |
| **Medium** | A few days to a week: caching layer, batching refactor, introducing concurrency, multiple files. |
| **High** | Multi-week or cross-team: cache infrastructure, schema migration, a native pushdown, or a new microservice with its own deploy/operate story. |

### Quadrant guide for recommending

- **High impact + Low risk + Low cost** → do first; these are the algorithmic wins and missing indexes.
- **High impact + High cost** → worth it but plan and phase it; re-measure before committing the effort.
- **High impact + High risk** → needs explicit sign-off, a benchmark gate, and a clear rollback (most concurrency and pushdown work).
- **Low impact** → usually defer regardless of cost; don't spend on Amdahl-capped wins while bigger bottlenecks remain.

---

## Self-review checklist

Run through this before handing the plan to the user.

### Measurement
- [ ] Every bottleneck is backed by a profiler run (tool + workload named) **or** explicitly marked estimated/static.
- [ ] A baseline number exists for the goal metric, and the workload is stated so it's reproducible.
- [ ] Bottlenecks are ranked by their share of runtime/cost, not by gut feel.

### Ladder discipline
- [ ] Each optimization names its rung and cites the bottleneck (file:line + measured/estimated cost) it addresses.
- [ ] No rung-4 micro-optimization or rung-5 pushdown is proposed on a path not shown to be hot.
- [ ] Cheaper rungs were exhausted before a more expensive one was proposed for the same path.
- [ ] Impact is anchored to the profiler share (no Amdahl-violating claims).

### Scoring & selection
- [ ] Every optimization has impact / risk / cost with a one-clause assumption; estimated impact is flagged.
- [ ] High-risk items (concurrency, cache invalidation, pushdowns) are called out for explicit sign-off.
- [ ] The user selected from `AskUserQuestion` before any plan was written.

### Plan & honesty
- [ ] Each phase has a reproducible before/after benchmark, not a "should be faster" claim.
- [ ] Correctness preservation is addressed; any change to outputs/ordering/precision/consistency is flagged.
- [ ] Re-measurement between phases is built in (optimizations interact).
- [ ] Pushdown proposals list their concrete risks (FFI/serialization/build/debug/ops/consistency).
- [ ] Unselected items are recorded as performance debt with their impact/risk/cost.
