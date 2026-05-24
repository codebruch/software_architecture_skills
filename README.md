# software_architecture_skills

Three Claude Code skills that work as a pipeline for understanding, improving, and verifying the architecture of an existing codebase.

## Skills

### `sw-architecture-writer`
Reverse-engineers a codebase and documents its architecture as ASCII diagrams plus a function complexity map. Produces four deliverables:

1. **Runtime architecture** — how components interact at runtime (HTTP, SQL, queues, etc.) with actors on the edges.
2. **Source code architecture** — package/module layout, one diagram per language, plus wiring artifacts (Dockerfile, compose, CI, IaC).
3. **Function complexity map** — table of non-trivial functions with file:line, LOC, cyclomatic complexity, and hotspot notes.
4. **Sequence diagrams** — important flows, with end users and external systems as actors.

### `sw-architecture-reviewer`
Reads architecture documents (typically the writer's output) and proposes improvements across four dimensions:

- **Simplicity** — kill over-engineering, shrink fat functions, drop dead config.
- **Testability** — separate pure logic from I/O so it can be tested without a stack.
- **Robustness** — input validation, fallbacks, safe failure, memory/race-condition risks.
- **Observability** — OpenTelemetry traces, structured logging, switchable debug mode.

For each improvement it scores **risk** and **cost**, then lets the user select which to pursue. Only for the selected items it draws the future-state architecture (runtime, source code, sequence diagrams) and produces a phased implementation plan with validation and rollback per phase.

### `sw-refactor-visualizer`
Runs *after* the reviewer's improvements have been implemented, and visualizes the impact. For each implemented improvement it produces:

- A **before/after mermaid diagram** when the change was structural (split functions, moved modules, added validation/fallback/tracing steps) — skipped when there's no structural footprint.
- A **complexity-reduction table** comparing the affected functions before vs after, with explicit deltas, measured the same way as the baseline.
- A **verdict** on whether the improvement met its original goal.

It ends with a roll-up: aggregate complexity delta, a per-dimension scorecard, and outstanding debt for anything not implemented.

## Install

Symlink or copy each skill folder into a Claude Code skills directory.

Globally (available everywhere):
```bash
ln -s "$(pwd)/sw-architecture-writer"    ~/.claude/skills/
ln -s "$(pwd)/sw-architecture-reviewer"  ~/.claude/skills/
ln -s "$(pwd)/sw-refactor-visualizer"    ~/.claude/skills/
```

Project-scoped (checked into a specific repo):
```bash
ln -s "$(pwd)/sw-architecture-writer"    <your-project>/.claude/skills/
ln -s "$(pwd)/sw-architecture-reviewer"  <your-project>/.claude/skills/
ln -s "$(pwd)/sw-refactor-visualizer"    <your-project>/.claude/skills/
```

## Usage

The skills auto-trigger from their descriptions, or invoke manually:

```
/sw-architecture-writer
/sw-architecture-reviewer
/sw-refactor-visualizer
```

Typical pipeline: run the **writer** against an unfamiliar codebase, feed its output to the **reviewer** to plan improvements, implement the selected ones, then run the **visualizer** to see the before/after impact and confirm complexity actually dropped.

## License

Apache License 2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE).
