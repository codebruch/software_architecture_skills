---
name: sw-architecture-writer
description: Reverse-engineer the architecture of an existing codebase and document it as ASCII diagrams plus a function complexity map. Use when the user asks to understand, document, map, diagram, or derive the architecture of an existing project, repo, or service from its source code.
---

# Software Architecture Writer

Your task is to understand an existing codebase and derive its architecture from the code itself — not from what docs claim, and not from what the code *should* be. Read the source, follow the wiring, then draw what's actually there.

## How to operate

1. **Survey first, draw later.** Before producing any diagram:
   - List the top-level layout (languages, build files, entry points).
   - Identify entry points: `main`, server bootstrap, CLI commands, HTTP handlers, message consumers, scheduled jobs.
   - Identify external boundaries: databases, queues, third-party APIs, file systems, other services.
   - Identify **actors** — humans (end users, admins, operators) and external systems that initiate interactions.
   - Identify the **existing tests**: framework, where they live, the command that runs them. You don't diagram tests, but the complexity map records which hotspots they cover.
   - **Scope large codebases explicitly.** If the repo is too big to read in full (a monorepo, hundreds of source files), don't sample silently. Map the top level, then either ask which subsystem matters or work one top-level module at a time (parallel subagents where available, each returning components and wires with file citations). State what was read in depth and what was only skimmed.

2. **Then produce the artifacts below.** All diagrams are ASCII. Use mermaid only if the user asks for it.

3. **Cite the code.** Every component on a diagram should be traceable to a file path. Use `path/to/file.ext:line` references next to component names so the reader can verify.

4. **Flag uncertainty.** If a wire is inferred rather than confirmed (e.g., "probably reads from this table"), mark it explicitly with `(?)` and a one-line note.

5. **Save it where the next skill can find it.** Write the deliverables to `docs/architecture/architecture.md` — or the repo's existing architecture-docs location, or wherever the user says — not only into the chat. The reviewer, test-suite-generator, optimizer, and refactor-visualizer skills all read this file later, often in a different session. Start it with a header:
   - **Commit and date** the docs describe (`git rev-parse --short HEAD`). `file:line` references rot as the code moves; the commit is what lets a later reader tell how stale they are, and what the refactor-visualizer diffs against.
   - **Scope** — whole repo, or which modules were read in depth.
   - **Measurement method** — the exact command used for the complexity map (or "counted by hand" with the rules). The visualizer re-runs the same command to compute honest before/after deltas.

## Required deliverables

Produce **all four**, with **at least one of each**. Do not skip a category — if a category genuinely doesn't apply (e.g., no external actors), say so explicitly.

### 1. Runtime architecture diagram(s)

How components interact while the system is running. Show:
- Processes / services / containers as boxes.
- Actors (users, external systems) on the edges.
- Data flow direction with arrows; label each arrow with the mechanism (HTTP, gRPC, SQL, Kafka topic, file write, etc.) and the purpose.

Example shape:

```
   ┌──────────┐  HTTPS /api/orders   ┌─────────────┐    SQL    ┌──────────┐
   │ End user │ ───────────────────▶ │  api-server │ ────────▶ │ postgres │
   └──────────┘                      │ cmd/api/... │ ◀──────── │  orders  │
                                     └──────┬──────┘           └──────────┘
                                            │ publish "order.created"
                                            ▼
                                     ┌──────────────┐
                                     │  Kafka topic │
                                     │   orders     │
                                     └──────────────┘
```

If the system has clearly distinct runtime modes (e.g., web request path vs. batch job), draw one diagram per mode.

### 2. Source code architecture diagram(s)

How code is organized — packages, modules, classes — and how they depend on each other.

- **One diagram per language.** If the repo has Go + TypeScript + Python, produce three diagrams.
- Show package/module boundaries and the direction of imports/dependencies.
- Group by layer or domain if the code is structured that way (handlers → services → repositories).

Under each diagram, add a short **module coupling table** — it is the evidence a later review needs to tell a well-used core from a tangle:

| Module | Depends on (fan-out) | Depended on by (fan-in) | Notes |
|--------|----------------------|-------------------------|-------|

Count internal modules only, from the imports. In Notes, flag dependency cycles, modules that skip a layer, and any module with both high fan-in and high fan-out (everything depends on it and it depends on everything). If git history is available, also list the pairs or groups of files that most often change in the same commit; files that always move together but live apart are worth knowing about.

Then, **for each artifact that wires multiple languages or components together** (Dockerfiles, docker-compose, Makefiles, Bazel BUILD files, CI pipelines, Terraform, Helm charts), add a separate small diagram or list showing what it composes and in what order.

Example:

```
go/
├── cmd/api          ─▶ internal/http ─▶ internal/service ─▶ internal/repo ─▶ (postgres)
│                                              │
│                                              ▼
│                                       internal/events ─▶ (kafka)
└── cmd/worker       ─▶ internal/worker ─▶ internal/service (shared)
```

### 3. Function complexity map

A table of the functions in the codebase with size and complexity. Cover the **non-trivial** functions — skip getters, setters, one-liners, generated code, and tests unless tests are the subject.

Columns:

| File:Line | Function | LOC | Cyclomatic complexity | Churn | Tests | Notes |
|-----------|----------|-----|-----------------------|-------|-------|-------|

- **LOC**: lines of code in the function body (exclude signature, blank lines, comments).
- **Cyclomatic complexity**: count of decision points + 1 (if, else if, case, &&, ||, for, while, catch, ternary). Use a tool if one is available for the language (`gocyclo`, `radon`, `lizard`, `eslint complexity`; `lizard` covers most languages in one run); otherwise count by hand and say so. Use one method for the whole table.
- **Churn**: commits touching the file in the last 12 months (`git log --since="12 months ago" --format= --name-only | sort | uniq -c | sort -rn`). Complex code that changes often is where bugs and effort concentrate; complex code nobody touches can usually wait. Omit the column if there is no git history.
- **Tests**: the test file that exercises the function, or `none`. Find it by searching the tests for references to the function or its callers; mark `(?)` when coverage is only indirect. The reviewer's risk scores and the test-suite-generator's priorities both lean on this column.
- **Notes**: flag hotspots — high complexity, high LOC, high churn, or functions that look like they do too much. A function that is complex, frequently changed, *and* untested is the top of the list.

If the codebase is large, scope the table: pick the top 20–30 by complexity, or scope to a module the user named. State the scope at the top of the table.

### 4. Sequence diagram(s) for important flows

For each important logic path, draw an ASCII sequence diagram. Pick flows that:
- Are user-facing or externally triggered.
- Cross multiple components.
- Encode core business logic, not boilerplate.

**Actors on the left must include end users or external systems** where applicable, not just internal components.

Example shape:

```
End user        api-server         OrderService         postgres        Kafka
   │                │                   │                  │              │
   │ POST /orders   │                   │                  │              │
   │───────────────▶│                   │                  │              │
   │                │ Create(order)     │                  │              │
   │                │──────────────────▶│                  │              │
   │                │                   │ INSERT orders    │              │
   │                │                   │─────────────────▶│              │
   │                │                   │◀─────────────────│ row          │
   │                │                   │ publish event    │              │
   │                │                   │─────────────────────────────────▶│
   │                │◀──────────────────│ Order{id}        │              │
   │◀───────────────│ 201 + body        │                  │              │
```

Pick at least one flow; aim for 3–5 if the system has that many distinct important paths.

## After drafting

Run through the [self-review checklist](checklist.md). If any category is missing or thin, fix it or explicitly note why it doesn't apply — don't quietly omit.
