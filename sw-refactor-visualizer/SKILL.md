---
name: sw-refactor-visualizer
description: Visualize the before/after impact of changes that were implemented from a sw-architecture-reviewer plan or a sw-performance-optimizer plan. For each implemented item, render a before-and-after mermaid diagram (when the change is structural) plus a table comparing the affected functions' complexity — or, for optimizations, the benchmark numbers — then check behavior was preserved and summarize the overall delta in a saved report. Use after the user has implemented some or all of an architecture review's or performance plan's recommendations and wants to see what actually changed and whether complexity dropped or the system got faster.
---

# Refactor Visualizer

You run *after* the improvements from a [[sw-architecture-reviewer]] plan — or the optimizations from a [[sw-performance-optimizer]] plan — have been implemented. Your job is to show, per improvement, what changed and whether it paid off — a before/after **mermaid diagram** when the change is structural, and a **complexity-reduction table** comparing the affected functions. You close the loop: writer → reviewer → implement → **visualize the result**.

This skill renders **mermaid**, not ASCII. The reviewer and writer default to ASCII; here the user wants diagrams that render. Mermaid does not render in a terminal, so the report is written to a markdown file — `docs/architecture/refactor-report.md` unless the user says otherwise — where GitHub, an IDE preview, or a notes app will draw it. In chat, give the verdicts and the roll-up, and point to the file.

## Inputs

You need three things. Ask for whatever is missing.

1. **The "before" baseline** — the architecture docs and function complexity map produced before the work (output of [[sw-architecture-writer]], normally `docs/architecture/architecture.md`). This is your source of *before* numbers and diagrams. Its header names the **baseline commit** and the **measurement command**; you need both.
2. **The plan** — the reviewer's findings table, selected improvements, and phased plan (`docs/architecture/review.md`), and/or the optimizer's baseline, scored table, and plan (`docs/architecture/performance.md`). This tells you *which* items to report on, by their original numbers, and what each was meant to achieve.
3. **The "after" state** — the current codebase, post-implementation. You read this directly to confirm what actually shipped and to re-measure.

If those files aren't where expected, ask. If the plan only ever existed in a chat that's gone, ask the user to list what they implemented and why, and say that verdicts against the "original goal" rest on that recollection.

If there is no before baseline, you cannot compare. Say so and offer to run [[sw-architecture-writer]] against the last commit before the work (e.g., a git tag or the commit prior to the refactor branch) to reconstruct it.

## Operating procedure

Work through these in order.

### Step 1 — Establish what was actually implemented

Start from the diff, not from a cold read: `git diff --stat <baseline commit>..HEAD` shows which files moved, and `git log <baseline commit>..HEAD` often names the improvement each commit served. Then cross-reference the plan against the current code. For each selected improvement, confirm it landed — cite the file/function where the change is visible. An improvement falls into one of:

- **Done** — implemented as planned.
- **Partial** — some of it landed; name what's missing.
- **Not done** — planned but not in the code. Report it as outstanding debt, don't fabricate a diagram for it.
- **Drifted** — implemented differently than planned. Describe what was done instead.

Only Done and Partial improvements get a before/after panel. A Drifted improvement gets one too when it serves the same goal by another route; judge it against the goal, not the planned route.

**Check that behavior was preserved.** Lower complexity is only a win if the system still does what it did. Run the test suite and report the result. Then look at how the tests themselves changed over the same range (`git diff <baseline commit>..HEAD -- <test dirs and snapshot files>`): assertions edited, tests deleted or skipped, and snapshots re-blessed during a refactor each mean either an intended behavior change or a regression that was accepted. List them and ask which, rather than assuming. If there is no test suite covering the touched code (see `docs/architecture/test-coverage-map.md` if [[sw-test-suite-generator]] was run), say plainly that behavior preservation is unverified.

### Step 2 — Re-measure complexity on the after state

Measure the *after* code with the **same method the before baseline used** — same tool (`gocyclo`, `radon`, `lizard`, `eslint complexity`) or same hand-count rules. Apples-to-apples or the deltas are meaningless. If the before numbers were hand-counted, hand-count the after numbers the same way and say so.

When a function was split, renamed, or moved, compare the **family**, not the survivor: the original function before, against everything its logic became after (the slimmed function plus each extracted piece, wherever it now lives). Report the family's total and its maximum. Comparing only the same-named function always shows a drop, because the rest of the complexity is now in rows you didn't count.

See [comparison-guide.md](comparison-guide.md) for what metric to compare per dimension — complexity reduction is the headline for simplicity/testability, but robustness/observability/security improvements *add* code on purpose, so measure the right thing (see below).

### Step 3 — Build a before/after panel per improvement

For each Done/Partial improvement, produce a panel with three parts:

**3a. Mermaid diagram — *if applicable*.**
Render a *before* and an *after* mermaid diagram when the improvement changed structure or flow:
- Split/extracted functions, moved modules, new layers → `graph` (source or runtime).
- Added validation, fallback, retry, tracing, or logging steps in a flow → `sequenceDiagram`.

Highlight what changed using the classes in [comparison-guide.md](comparison-guide.md) (`new`, `changed`, `removed`). Caption each pair with the improvement number and one line on what to look at.

**Skip the diagram** when the change has no structural footprint (e.g., bounding a cache size, swapping a log format, adding a metric to an existing call). Say "no structural change — see table" and go straight to the metrics. Don't draw a diagram that looks identical before and after just to have one.

**3b. Complexity-reduction table.**
Compare the affected functions/components, before vs after, with an explicit delta. Default columns:

| File:Line | Function | LOC before → after | Cyclomatic before → after | Δ | Notes |
|-----------|----------|--------------------|---------------------------|---|-------|

- Show the delta and, for the headline metric, the percent change.
- If complexity went **up** by design (added validation/fallback/observability/access checks), say so and show the metric that *did* improve instead (see [comparison-guide.md](comparison-guide.md)) — e.g., "cyclomatic +3, but 4 previously-unhandled inputs now rejected at the boundary".

**For a performance optimization**, the table is a benchmark comparison instead: re-run the optimizer's recorded command on the recorded workload, with the same [hygiene](comparison-guide.md#performance-items) as the baseline, and show metric, before, after, change, and run-to-run spread. If the original workload or command can't be reproduced, re-measure *both* sides the same way (check out the baseline commit for the before number) rather than comparing a new measurement with an old one.

**3c. Verdict.**
One or two lines: did this improvement achieve its intent? Reference the original goal from the reviewer's plan. Be honest — "split landed but the I/O is still inline in `calc_total`, so it's still not unit-testable" is more useful than a green checkmark.

### Step 4 — Roll-up summary

After the per-improvement panels:

- **Aggregate complexity delta** — across all touched functions, before vs after: total LOC, total cyclomatic, the maximum single-function cyclomatic, and how many functions sit above the hotspot threshold (CC > 10). One summary table. Don't headline the *average*: splitting one function into three lowers the average even when nothing got simpler.
- **Dimension scorecard** — for each of the reviewer's dimensions (simplicity, testability, robustness, observability, security), a one-line before/after statement. Add a performance line (goal metric before → after) when optimizer items are in scope.
- **Behavior preservation** — test-suite result, plus any assertions, tests, or snapshots that changed during the work and whether each was intended.
- **Outstanding debt** — improvements that were Not done or Partial, carried forward with their original scores from the plan's table. Security items that are Not done or Partial go first, each with what remains exposed.
- **Regressions or surprises** — anything that got worse, or any complexity that moved somewhere else rather than disappearing (e.g., a fat function split into three that are each fine, but a new orchestrator now carries the branching).

## Anti-patterns to avoid

- **Decorative diagrams.** A before/after pair that looks the same is noise. Only draw when structure changed; otherwise show the number.
- **Mismatched measurement.** Re-measuring the after code with a different tool or rule than the before baseline. The delta is the whole point — it must be honest.
- **Claiming wins that didn't land.** If the code doesn't show the change, it's Not done. Don't draw the planned target as if it were reality.
- **Hiding complexity that just moved.** Splitting a function isn't a win if the complexity reappeared in a new coordinator. Track where it went.
- **Scoring structure while ignoring behavior.** A refactor that halves complexity and quietly re-blesses a dozen snapshots changed what the system does. Report that next to the complexity win, not instead of it.
- **Comparing a new benchmark with an old number.** Different machine, data, or command, and the "speedup" is an artifact. Same command on both sides or it isn't a comparison.
- **Treating added code as failure.** Robustness, observability, and security improvements raise LOC/complexity on purpose. Judge them by the right metric, not by raw line count.
