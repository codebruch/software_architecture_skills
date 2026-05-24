# Self-review checklist

Run through this before handing the architecture write-up to the user.

## Coverage

- [ ] All four deliverables present: runtime diagram, source code diagram(s), function complexity table, sequence diagram(s).
- [ ] At least one source code diagram **per language** in the repo.
- [ ] Wiring artifacts (Dockerfile, docker-compose, Makefile, CI, IaC) are diagrammed or listed if they exist.
- [ ] Actors (end users, external systems, operators) appear on runtime and sequence diagrams where applicable.

## Fidelity to the code

- [ ] Every component on a diagram is traceable to a file path (cited inline).
- [ ] Inferred / unverified wires are marked with `(?)` and a note.
- [ ] No components are drawn that don't actually exist in the code.
- [ ] No flows are drawn that don't actually execute.

## Function complexity table

- [ ] Scope of the table is stated (whole repo, top-N, specific module).
- [ ] LOC and complexity numbers state how they were measured (tool name, or "counted by hand").
- [ ] Trivial functions (getters, one-liners, generated code) are excluded.
- [ ] Hotspots are flagged in the Notes column, not buried.

## Diagram quality

- [ ] Arrows are labeled with mechanism + purpose ("HTTPS POST /orders"), not bare lines.
- [ ] Sequence diagrams have time flowing top-to-bottom, actors across the top.
- [ ] ASCII is readable in monospace; no broken box-drawing characters.
- [ ] One concept per diagram — don't merge runtime and source-code views into a single picture.

## Honesty

- [ ] Things that couldn't be determined from the code are called out, not guessed silently.
- [ ] If a required deliverable category genuinely doesn't apply, that is stated explicitly with the reason.
