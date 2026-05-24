---
name: sw-refactor-visualizer
description: Visualize the before/after impact of architecture improvements that were implemented from a sw-architecture-reviewer plan. For each implemented improvement, render a before-and-after mermaid diagram (when the change is structural) plus a complexity-reduction table comparing the affected functions, then summarize the overall delta. Use after the user has implemented some or all of an architecture review's recommendations and wants to see what actually changed and whether complexity dropped.
---

# Refactor Visualizer

You run *after* the improvements from a [[sw-architecture-reviewer]] plan have been implemented. Your job is to show, per improvement, what changed and whether it paid off — a before/after **mermaid diagram** when the change is structural, and a **complexity-reduction table** comparing the affected functions. You close the loop: writer → reviewer → implement → **visualize the result**.

This skill renders **mermaid**, not ASCII. The reviewer and writer default to ASCII; here the user wants diagrams that render.

## Inputs

You need three things. Ask for whatever is missing.

1. **The "before" baseline** — the architecture docs and function complexity map produced before the work (output of [[sw-architecture-writer]]) and the reviewer's findings table. This is your source of *before* numbers and diagrams.
2. **The implementation plan** — the reviewer's selected improvements and phased plan. This tells you *which* improvements to report on, by their original numbers.
3. **The "after" state** — the current codebase, post-implementation. You read this directly to confirm what actually shipped and to re-measure.

If there is no before baseline, you cannot compare. Say so and offer to run [[sw-architecture-writer]] against the last commit before the work (e.g., a git tag or the commit prior to the refactor branch) to reconstruct it.

## Operating procedure

Work through these in order.

### Step 1 — Establish what was actually implemented

Cross-reference the reviewer's plan against the current code. For each selected improvement, confirm it landed — cite the file/function where the change is visible. An improvement falls into one of:

- **Done** — implemented as planned.
- **Partial** — some of it landed; name what's missing.
- **Not done** — planned but not in the code. Report it as outstanding debt, don't fabricate a diagram for it.
- **Drifted** — implemented differently than planned. Describe what was done instead.

Only Done and Partial improvements get a before/after panel.

### Step 2 — Re-measure complexity on the after state

Measure the *after* code with the **same method the before baseline used** — same tool (`gocyclo`, `radon`, `lizard`, `eslint complexity`) or same hand-count rules. Apples-to-apples or the deltas are meaningless. If the before numbers were hand-counted, hand-count the after numbers the same way and say so.

See [comparison-guide.md](comparison-guide.md) for what metric to compare per dimension — complexity reduction is the headline for simplicity/testability, but robustness/observability improvements *add* code on purpose, so measure the right thing (see below).

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
- If complexity went **up** by design (added validation/fallback/observability), say so and show the metric that *did* improve instead (see [comparison-guide.md](comparison-guide.md)) — e.g., "cyclomatic +3, but 4 previously-unhandled inputs now rejected at the boundary".

**3c. Verdict.**
One or two lines: did this improvement achieve its intent? Reference the original goal from the reviewer's plan. Be honest — "split landed but the I/O is still inline in `calc_total`, so it's still not unit-testable" is more useful than a green checkmark.

### Step 4 — Roll-up summary

After the per-improvement panels:

- **Aggregate complexity delta** — total LOC and average cyclomatic across all touched functions, before vs after. One summary table.
- **Dimension scorecard** — for each of the four dimensions (simplicity, testability, robustness, observability), a one-line before/after statement.
- **Outstanding debt** — improvements that were Not done or Partial, carried forward with their original risk/cost from the reviewer's table.
- **Regressions or surprises** — anything that got worse, or any complexity that moved somewhere else rather than disappearing (e.g., a fat function split into three that are each fine, but a new orchestrator now carries the branching).

## Anti-patterns to avoid

- **Decorative diagrams.** A before/after pair that looks the same is noise. Only draw when structure changed; otherwise show the number.
- **Mismatched measurement.** Re-measuring the after code with a different tool or rule than the before baseline. The delta is the whole point — it must be honest.
- **Claiming wins that didn't land.** If the code doesn't show the change, it's Not done. Don't draw the planned target as if it were reality.
- **Hiding complexity that just moved.** Splitting a function isn't a win if the complexity reappeared in a new coordinator. Track where it went.
- **Treating added code as failure.** Robustness and observability improvements raise LOC/complexity on purpose. Judge them by the right metric, not by raw line count.
