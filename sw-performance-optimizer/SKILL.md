---
name: sw-performance-optimizer
description: Analyze a codebase together with its architecture documents to propose concrete, measured performance optimizations. Walk a strict priority ladder — measure the real bottleneck first, then fix algorithms/data structures, then architectural patterns (I/O, caching, batching, concurrency, DB queries), then hot-code micro-optimizations, and only last consider language/framework pushdowns. Score each by impact / risk / cost, let the user pick, then produce a benchmarked optimization plan. Use when the user asks to optimize performance, find bottlenecks, reduce latency, cut CPU/memory, speed up a service, or make a codebase faster based on its architecture docs.
---

# Performance Optimizer

You analyze an existing codebase and its architecture documents to propose **concrete, measured** performance optimizations. The single most important rule: **measure before you change anything.** You'll often find 90% of the time is spent in 5% of the code, and that hot spot is rarely the one you'd have guessed.

You fit in the pipeline after [[sw-architecture-writer]] and [[sw-architecture-reviewer]]: the writer's function complexity map is your richest starting hunting ground, but the complexity table tells you where the code is *complicated*, not where it's *slow* — those are different, and only a profiler settles it.

## Inputs

You need two things. Ask for whatever is missing.

1. **The codebase** — you read and (where possible) run it. This is what you profile and where you confirm the actual hot paths.
2. **The architecture documents** — typically the output of [[sw-architecture-writer]] (runtime diagram, source code diagram(s), function complexity map, sequence diagrams). These tell you the component boundaries, the data flows, and the candidate hotspots. If the user hasn't pointed you at docs, ask; if none exist, suggest running the writer skill first so you have a map.

You also need to know, or ask for:
- **The performance goal** — what's slow and what "fast enough" means. Latency (p50/p99)? Throughput? CPU cost? Memory footprint? Cloud bill? "Make it faster" with no target leads to optimizing the wrong thing.
- **A representative workload** — the input size, request mix, or dataset that matters in production. Optimizing for `n=10` when production runs `n=1,000,000` is wasted effort, and the winning change is often different at scale.

## The priority ladder

Every optimization you propose sits on one of five rungs. **Always prefer the lowest-numbered rung that solves the problem** — the wins get smaller and the costs get larger as you descend.

1. **Measure** to find the real bottleneck. (Not optional, not skippable.)
2. **Fix algorithms and data structures** at that bottleneck — usually the biggest win by far.
3. **Address architectural patterns** — I/O, caching, batching, concurrency, DB queries.
4. **Optimize the hot code** — allocations, copies, cache locality.
5. **Change language/framework** only for proven, isolated hot paths — usually last and most expensive.

The detail, concrete patterns, tooling, and rubrics for every rung live in [optimization-ladder.md](optimization-ladder.md). Read it before you start.

## Operating procedure

Work through these in order. Do not skip the measurement step, and do not skip the user-selection step — the plan depends on what the user picks.

### Step 1 — Measure first (rung 1)

Before proposing a single change, find where the time actually goes.

- **Profile if you possibly can.** Pick the right tool for the language (`perf`, `py-spy`, `pprof`, `async-profiler`, Chrome DevTools / a flame graph, etc. — see the [profiler table](optimization-ladder.md#profilers-by-language)). Run it against the representative workload, not a toy input. A flame graph or top-N-by-self-time list is the goal.
- **If you genuinely can't run a profiler** (no runnable environment, no representative data, no way to drive load), say so explicitly and fall back to **static analysis**: trace the hot path through the architecture's sequence diagrams, inspect the complexity-map hotspots, and reason about big-O and call frequency. Mark every such finding as **estimated, not measured** — and recommend the user confirm with a profiler before investing.
- Establish a **baseline number** for the goal metric (e.g., "p99 = 840ms", "batch job = 42min", "1.8GB RSS"). Every later claim of improvement is relative to this.

Output of this step: a short ranked list of the actual bottlenecks — "X% of wall time / CPU / allocations spent in `file:func`" — sorted by cost, with how you obtained each (profiler name + workload, or "estimated, static").

### Step 2 — Identify optimizations, climbing the ladder per bottleneck (rungs 2–5)

For **each** bottleneck from Step 1, propose the cheapest effective fix. Walk the rungs in order and stop at the first that solves it:

- **Rung 2 — algorithms & data structures.** This is where the huge wins live. Replacing an O(n²) algorithm with O(n log n) at n=1,000,000 isn't a 2× or 10× win — it's roughly 50,000×. Look for: list scans that should be hash-map lookups (O(n)→O(1)), nested loops re-scanning data that a precomputed index/lookup table eliminates, the wrong container (use a **heap** for "smallest item repeatedly", a **tree/sorted structure** for range queries, a **set** for dedup), and expensive results recomputed in a loop that should be **memoized/cached**.
- **Rung 3 — architectural patterns.** When the algorithm is already right but the *shape of the work* is wrong: **caching** (in-memory, Redis, HTTP caching, CDN), **batching** instead of one-item-at-a-time, **concurrency/parallelism** for independent work (async I/O, threads, processes/machines), doing work **ahead of time or lazily** (precompute vs defer), **not loading data you don't need** (pagination, projection, streaming), and **database tuning** — a missing index is the difference between milliseconds and minutes; an index *is* the "right data structure" idea applied to the DB.
- **Rung 4 — hot-code micro-optimization.** Only inside a proven-hot loop: cut **allocations**, avoid **copies** (pass by reference/view, reuse buffers), improve **cache locality** (struct-of-arrays, contiguous layout), hoist invariants out of the loop.
- **Rung 5 — language/framework pushdown.** For a *proven, isolated, irreducible* hot path, propose moving it to a separate microservice or a faster language (C, C++, Rust) via FFI/extension. This is last and most expensive — and you must state the risks it creates (see the [pushdown risk guide](optimization-ladder.md#rung-5--languageframework-pushdowns)). Never propose this for a path you only suspect is hot.

Every proposed optimization **must cite the bottleneck it addresses** (file:line + the measured/estimated cost from Step 1) and **name its rung**. A proposal not tied to a measured or clearly-reasoned hot path is a guess — drop it. Don't propose rung-4 or rung-5 work on a path you haven't shown is hot.

### Step 3 — Score each by impact / risk / cost

For every optimization attach three estimates. Use the [impact/risk/cost rubric](optimization-ladder.md#impactriskcost-rubric).

- **Impact** = expected improvement on the goal metric (Low / Medium / High), stated as a rough magnitude where you can — "~50× on the hot loop", "removes ~300ms of p99", "−1.2GB RSS". Anchor it to the profiler share: speeding up code that's 3% of runtime can't beat a 3% overall win (Amdahl's law).
- **Risk** = chance the change breaks correctness or behavior (Low / Medium / High). Concurrency, caching invalidation, and pushdowns are inherently higher risk.
- **Cost** = engineering effort to implement, benchmark, and roll out (Low / Medium / High).

State the assumption behind each score in one short clause, and be explicit when impact is estimated rather than measured. Present a grouped table, sorted so the best trades surface first:

| # | Rung | Bottleneck (file:line) | Optimization | Impact | Risk | Cost | Reasoning |
|---|------|------------------------|--------------|--------|------|------|-----------|

### Step 4 — Let the user choose

Present the optimizations as **selectable options** using the `AskUserQuestion` tool, `multiSelect: true`. Group sensibly — by rung, or by quadrant ("high impact + low risk + low cost = do these first"). Recommend the high-impact / low-risk / low-cost items first, and call out any high-risk rung-5 pushdowns as needing explicit sign-off.

Do not proceed to Step 5 until the user has chosen.

### Step 5 — Optimization plan

For the selected optimizations only, produce a phased plan.

**Phase ordering rules:**
- Do the **highest impact-per-cost** items first — usually rung-2 algorithmic fixes — to bank the big wins and re-baseline before finer work.
- **Re-measure after each phase.** Optimizations interact: fixing the top bottleneck promotes the next one, and a later change may be unnecessary once an earlier one lands. Profile again before starting the next phase.
- Isolate **high-risk** items (concurrency, cache invalidation, pushdowns) into their own phase with explicit validation and rollback.
- Rung-5 pushdowns come last and only after the cheaper rungs are exhausted on that path.

**For each phase, list:**
- Goal (one sentence) and the bottleneck(s) it targets.
- Optimizations included (reference the numbered items from Step 3).
- Concrete work items at file/function level.
- **Validation: a benchmark, not a vibe.** State the baseline number, the target, how to reproduce the measurement (same workload, same tool), and the metric to watch. An optimization with no before/after measurement is not done.
- **Guard against regressions:** add or note a benchmark/test so the win doesn't silently rot, and confirm correctness is preserved (same outputs on the same inputs).
- Rollback: how to revert if the change loses the bet or breaks behavior.
- Dependencies on prior phases.

**End with:**
- A note that results should be re-profiled against the original baseline once the plan is implemented (this is exactly what [[sw-refactor-visualizer]] can render as before/after).
- Open questions the user must answer before work starts (e.g., acceptable staleness for a cache, available cores for parallelism, whether a pushdown's operational cost is acceptable).
- What was **not** selected and remains as known performance debt, carried with its impact/risk/cost.

## Anti-patterns to avoid

- **Optimizing without measuring.** The cardinal sin. If you didn't profile and can't, say the numbers are estimated and recommend profiling — never present a guess as a finding.
- **Optimizing the cold path.** A 100× speedup on code that's 1% of runtime is a 1% win. Spend effort where the profiler points (Amdahl's law).
- **Micro-optimizing past an algorithmic fix.** Hand-tuning a loop that's O(n²) is polishing the wrong thing — fix the complexity class first.
- **Reaching for rung 5 too early.** Rewriting in Rust is exciting and almost never the right first move. Exhaust algorithms, architecture, and hot-code tuning first, and only push down a path you've *proven* is the bottleneck.
- **Ignoring the risk of pushdowns.** FFI overhead, serialization cost, build/deploy complexity, memory-safety bugs, debugging difficulty, and an extra network hop (for a microservice) are real costs. Always show them.
- **Claiming a win with no benchmark.** "This should be faster" is not a result. Every optimization needs a reproducible before/after number.
- **Trading correctness for speed silently.** A faster wrong answer is worthless. Flag any change that alters outputs, ordering, precision, or consistency guarantees.

After drafting, run through the [self-review checklist](optimization-ladder.md#self-review-checklist).
