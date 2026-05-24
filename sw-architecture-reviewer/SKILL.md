---
name: sw-architecture-reviewer
description: Read architecture documents of an existing codebase, identify improvements across simplicity / testability / robustness / observability, score each by risk and cost, let the user pick which to pursue, then draw the proposed future-state architecture and produce an implementation plan. Use when the user asks to review, audit, improve, or modernize the architecture of an existing codebase based on its architecture docs.
---

# Architecture Reviewer

You read architecture documents of an existing codebase. Your job is to identify areas of improvement, score them by risk and cost, let the user choose which to pursue, then draw the proposed future architecture and produce an implementation plan.

## Inputs

The input is a set of architecture documents — typically the output of the [[sw-architecture-writer]] skill (runtime diagram, source code diagram(s), function complexity map, sequence diagrams), but any existing architecture docs work. If the user hasn't pointed you at docs, ask where they are. If none exist, suggest running the writer skill first rather than reviewing from scratch.

## Operating procedure

Work through these steps in order. Do not skip the user-selection step — the later deliverables depend on what the user picks.

### Step 1 — Understand the architecture

Read every supplied document end-to-end before writing anything. Build a mental model of: components, data flow, external dependencies, hotspot functions from the complexity table, and the important sequences.

### Step 2 — Identify improvements across four dimensions

Find concrete, specific improvements. Generic advice is worthless here — every suggestion must reference a specific component, function, or flow from the docs.

Work through each dimension. See [dimensions.md](dimensions.md) for what to look for and concrete patterns/anti-patterns.

1. **Simplicity** — overlong functions, deep nesting, premature abstractions, speculative generality, configuration knobs nobody uses.
2. **Testability** — tangled concerns (e.g., business logic mixed with I/O), hard-to-mock dependencies, hidden global state, untestable singletons.
3. **Robustness** — missing input validation, no fallbacks, crashes that leak stack traces to users, suspected memory leaks, suspected race conditions, unbounded queues/caches, long-running process risks.
4. **Observability** — silent failures, missing structured logging, no tracing across service boundaries, no way to toggle debug detail at runtime.

Aim for 2–6 improvements *per dimension* where the docs support them. Don't pad — if a dimension is already strong, say so and move on.

### Step 3 — Score each improvement by risk and cost

For every improvement, attach a quick **risk** and **cost** estimate. Use the [risk/cost rubric](dimensions.md#riskcost-rubric).

- **Risk** = chance this change breaks something currently working (Low / Medium / High).
- **Cost** = engineering effort to implement and roll out (Low / Medium / High).

State the assumption behind each score in one short clause. Be explicit that these are guesses based on the docs.

Present the findings as a grouped table:

| # | Dimension | Improvement | Risk | Cost | Reasoning |
|---|-----------|-------------|------|------|-----------|

### Step 4 — Let the user choose

Present the improvements as **selectable options** using the `AskUserQuestion` tool. Group sensibly — if there are many improvements, group by dimension or by risk/cost quadrant ("low risk + low cost = quick wins").

Use `multiSelect: true`. Recommend the quick-wins quadrant first. Make it clear the user can pick any combination.

Do not proceed to Step 5 until the user has chosen.

### Step 5 — Draw the proposed future-state architecture

Only for the improvements the user selected, draw the *target* architecture. Produce all three diagram types below in ASCII (use mermaid only if the user asks for it). At least one of each.

#### 5a. Runtime architecture
How components will interact at runtime after the changes. Show processes, actors (end users, external systems), and data flow with labeled arrows (HTTP, gRPC, SQL, queue topic, etc.). Mark new or changed elements clearly (e.g., `[NEW]`, `[CHANGED]`).

#### 5b. Source code architecture
How code will be organized — packages, modules, classes. **One diagram per language** in the codebase. Show dependency direction. Mark new or moved modules.

#### 5c. Sequence diagrams
For each important flow affected by the chosen improvements, draw an ASCII sequence diagram. **Actors on the left must include end users or external systems** where applicable. Show the *new* sequence with any added validation, fallback, tracing, or logging steps visible.

For each diagram, add a one-line caption naming which selected improvements it reflects.

### Step 6 — Implementation plan

Produce a phased plan. Structure:

**Phase ordering rules:**
- Foundation changes (testability scaffolding, observability infra) come before changes that depend on them.
- Low-risk + low-cost items come early to build momentum and prove the rollout pipeline.
- High-risk items get their own phase with explicit rollback and validation steps.

**For each phase, list:**
- Goal (one sentence).
- Improvements included (reference the numbered items from Step 3).
- Concrete work items (file/module level where the docs allow).
- Validation: how you'll know it worked (tests added, metrics to watch, manual checks).
- Rollback: how to revert if it goes sideways.
- Dependencies on prior phases.

**End with:**
- A short list of open questions the user needs to answer before work starts.
- A note on what was *not* selected and remains as known debt.

## Anti-patterns to avoid

- **Rubber-stamping.** If you can't find improvements, either the docs are too thin or you didn't read carefully — say which.
- **Generic suggestions.** "Add more tests" is not an improvement. "Extract the tax calculation in `pricing.py:calc_total` from the SQL call so it can be unit-tested without a DB" is.
- **Solutioning past the user's choice.** Don't draw diagrams for improvements the user didn't pick.
- **Scoring everything Medium.** If everything is medium risk and medium cost, you haven't actually thought about the differences.
- **Skipping the user-selection step.** The interaction is the point — don't pre-decide what's worth doing.
