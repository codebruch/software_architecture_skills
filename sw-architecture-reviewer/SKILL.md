---
name: sw-architecture-reviewer
description: Read architecture documents of an existing codebase, identify improvements across simplicity / testability / robustness / observability, verify them against the code, score each by benefit, risk and cost, let the user pick which to pursue, then draw the proposed future-state architecture and produce an implementation plan. Use when the user asks to review, audit, improve, or modernize the architecture of an existing codebase based on its architecture docs.
---

# Architecture Reviewer

You read architecture documents of an existing codebase. Your job is to identify areas of improvement, confirm them in the code, score them by benefit, risk, and cost, let the user choose which to pursue, then draw the proposed future architecture and produce an implementation plan.

## Inputs

The input is a set of architecture documents — typically the output of the [[sw-architecture-writer]] skill (runtime diagram, source code diagram(s), function complexity map, sequence diagrams), but any existing architecture docs work. Look in `docs/architecture/architecture.md` first; if nothing is there and the user hasn't pointed you at docs, ask where they are. If none exist, suggest running the writer skill first rather than reviewing from scratch.

You also need the **codebase itself**, to check findings against (Step 2). And check how stale the docs are before trusting them: if the docs header names a commit, compare it with the current code (`git diff --stat <commit>..HEAD`). If the areas you're reviewing have moved substantially, say so and offer to re-run the writer rather than reviewing a system that no longer exists.

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

**Verify each candidate against the code before it goes in the table.** The docs tell you where to look; only the code tells you whether it's true. Diagrams and a complexity table can't show a swallowed exception, a missing validation, or a config knob nobody reads. Open the cited `file:line` and confirm the problem exists as you described it. Drop candidates the code contradicts, and tag each survivor `confirmed` (seen in the code) or `inferred` (docs only, because the code wasn't available or the path couldn't be traced).

### Step 3 — Score each improvement by benefit, risk, and cost

For every improvement, attach a quick **benefit**, **risk**, and **cost** estimate. Use the [benefit/risk/cost rubric](dimensions.md#benefitriskcost-rubric).

- **Benefit** = how much real pain this removes (Low / Medium / High). Cheap and safe is not the same as worth doing: anchor benefit in evidence — the function is a high-churn hotspot, the failure mode loses data or pages someone, the tangle blocks testing a core flow.
- **Risk** = chance this change breaks something currently working (Low / Medium / High). Use the complexity map's Tests column: changing untested code is riskier than the same change under tests.
- **Cost** = engineering effort to implement and roll out (Low / Medium / High).

State the assumption behind each score in one short clause. Be explicit that these are estimates.

Present the findings as a grouped table:

| # | Dimension | Improvement | Evidence | Benefit | Risk | Cost | Reasoning |
|---|-----------|-------------|----------|---------|------|------|-----------|

Evidence is the `file:line` plus `confirmed` or `inferred`.

### Step 4 — Let the user choose

Present the improvements as **selectable options** using the `AskUserQuestion` tool. Group sensibly — if there are many improvements, group by dimension or by risk/cost quadrant ("low risk + low cost = quick wins").

Use `multiSelect: true`. Recommend the high-benefit quick wins first. Make it clear the user can pick any combination.

The tool holds at most 4 questions of at most 4 options each, and option labels are only a few words, so a long findings table won't fit verbatim. Ask one question per group, label each option with its table number and a short name (`#3 Extract tax calc`), and put the benefit/risk/cost trade-off in the option description. When a group has more than four items, offer its strongest four and say that any other item can be added by number through "Other". If the tool isn't available (a non-interactive run), print the numbered table and ask for a list of numbers instead.

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
- **Safety net first.** If a selected improvement changes code the complexity map marks as untested, or is scored Medium/High risk, the plan opens with a phase that pins the current behavior of those paths with characterization tests ([[sw-test-suite-generator]]). Every later phase's validation then includes "that suite stays green, with no assertion or snapshot re-blessed".
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

### Step 7 — Save the review

Write the full findings table (every item, with the selected ones marked), the target diagrams, and the plan to `docs/architecture/review.md`, next to the architecture docs, and record the commit the review was made against. [[sw-refactor-visualizer]] needs exactly this file after the work is implemented — the item numbers, the original scores, and the stated goals — and by then the chat it was produced in is gone.

## Anti-patterns to avoid

- **Reviewing the diagram instead of the system.** A finding you didn't check against the code is a hypothesis. Mark it `inferred` or verify it.
- **Recommending the cheap over the valuable.** Low risk and low cost don't justify a change that removes no real pain. Benefit comes first.
- **Rubber-stamping.** If you can't find improvements, either the docs are too thin or you didn't read carefully — say which.
- **Generic suggestions.** "Add more tests" is not an improvement. "Extract the tax calculation in `pricing.py:calc_total` from the SQL call so it can be unit-tested without a DB" is.
- **Solutioning past the user's choice.** Don't draw diagrams for improvements the user didn't pick.
- **Scoring everything Medium.** If everything is medium benefit, medium risk, and medium cost, you haven't actually thought about the differences.
- **Skipping the user-selection step.** The interaction is the point — don't pre-decide what's worth doing.
