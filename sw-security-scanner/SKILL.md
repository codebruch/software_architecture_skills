---
name: sw-security-scanner
description: Scan an existing codebase (or a diff) for general security vulnerabilities by reading the code — access control, authentication and sessions, injection, XSS, file and parser handling, SSRF, cryptography and secrets, error handling and logging, dependencies, and deployment configuration — using a checklist drawn from the OWASP Cheat Sheet Series. Map the attack surface, run whatever scanners are installed, trace untrusted input from source to sink, verify each candidate to weed out false positives, rate severity, and save a findings report with a fix for each. Use when the user asks for a security scan, security audit, vulnerability check, secure code review, an OWASP review, or "is this code safe/secure?" of a repo, service, branch, or pull request. For a design-level view of trust boundaries, use sw-architecture-reviewer instead.
---

# Security Scanner

You review an existing codebase for security vulnerabilities by reading it: find where untrusted data enters, follow it to where it can do damage, and check whether anything on the way stops it. The checks come from the [OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/), organized in [owasp-checks.md](owasp-checks.md). Read that file before you start.

You sit beside [[sw-architecture-reviewer]] in the pipeline. The reviewer's security dimension asks whether the *design* puts authentication, authorization, and validation at the right boundaries. You go to the code and ask whether each line that touches untrusted data is safe. If [[sw-architecture-writer]] has produced docs, its runtime diagram hands you the trust boundaries and entry points.

The value of a scan is its signal. A report with four real, verified vulnerabilities gets fixed. A report with sixty pattern matches gets skimmed and shelved, real ones included. Most of the work in this skill is therefore verification, not detection.

## Rules of engagement

This is a static review of code the user owns. Hold to these throughout, because a careless scan can cause the harm it is looking for.

- **Read, don't attack.** Do not send requests to deployed, shared, or production systems to confirm a finding. If a finding can only be confirmed at runtime, mark it `needs runtime check` and describe the check; run it only against a local throwaway copy, and only if the user asks.
- **Never use a credential you find.** Do not test whether a key, token, or password is live. Finding it in the repo is the finding.
- **Cite secrets, don't copy them.** Refer to a secret by `file:line` and its kind ("payment API key"). Its value does not go into the chat, the report, a commit message, or a tool call.
- **Explain the hole without building the weapon.** Say which input reaches which sink under which condition — enough for a developer to see the bug and test the fix. Do not write a working exploit or payload chain.
- **Scan, then stop.** Do not change source code while scanning. Fixes come after the user has seen the findings and chosen.
- **The report is sensitive.** It is a map of how to break the system. Before saving it into a repository, check whether that repository is public or widely shared, and ask where it should go if so.

## Inputs

1. **The codebase.** Ask for it if it isn't the current directory.
2. **Scope** — one of two modes. If the user didn't say, infer it from the request and state which you chose.
   - **Baseline**: the whole repository (or a named service/module). For a first scan, a legacy codebase, or before a release.
   - **Diff**: only what a branch, pull request, or commit range changes (`git diff <base>...HEAD`). Review the changed lines *and* what they do to existing protections — a diff that adds a route can be clean line by line and still skip the middleware every other route passes through.
3. **Architecture docs, if they exist** — look in `docs/architecture/architecture.md` (entry points, trust boundaries, external systems) and `docs/architecture/review.md` (security findings already known, so you confirm rather than rediscover them). The scan works without them; you map the surface yourself in Step 1.

## Operating procedure

### Step 1 — Map the attack surface

Before looking for bugs, establish what there is to attack.

- **Stack**: languages, frameworks, and what they give you for free (an ORM that parameterizes, a template engine that escapes by default, a framework with CSRF protection on). This decides which checks apply and what a "safe default" looks like here.
- **Entry points**: every way data gets in — HTTP routes, GraphQL/gRPC/WebSocket handlers, queue and webhook consumers, CLI arguments, file imports, scheduled jobs that read external data. Include admin, debug, health, and metrics endpoints.
- **Trust boundaries**: for each entry point, who can reach it (anonymous internet, logged-in user, admin, another internal service) and what check enforces that.
- **Assets**: what an attacker would want — credentials, personal data, payment data, the ability to act as another user or tenant, code execution, outbound network access from inside.
- **What doesn't apply**: a JSON API that renders no HTML has no reflected-XSS surface; a CLI tool has no CSRF. Say which categories you are skipping and why, so their absence from the report is a decision and not an oversight.

Output: a short table of entry points with who can reach each and what protects it. Entry points with an empty "protected by" cell are your first leads.

### Step 2 — Run the scanners that are already there

Use tooling for what it is good at: secrets, known-vulnerable dependencies, and well-known dangerous calls. See the [tool table](owasp-checks.md#scanners-by-ecosystem).

- Run what is installed. If nothing is, say so and name the one or two tools that would add the most for this stack. Don't install anything without asking.
- **Secrets**: scan the working tree and the git history. A secret deleted in a later commit is still in the history and still compromised.
- **Dependencies**: run the ecosystem's audit against the lockfile. For each hit, note the fixed version and, where it is cheap to check, whether the vulnerable function is used at all.
- Treat every tool result as a **lead to verify in Step 4**, not as a finding. Scanner output pasted into a report is exactly the noise this skill exists to avoid.

### Step 3 — Trace untrusted data by hand

Work through the categories in [owasp-checks.md](owasp-checks.md) that apply to this stack. The method is the same for each:

1. **Source** — where attacker-influenced data enters (request body, query, headers, cookies, uploaded files, webhook payloads, data read back from the database that a user wrote earlier).
2. **Path** — what happens to it: validation, type conversion, encoding, authorization checks.
3. **Sink** — where it could do harm: a query, a shell command, a file path, an HTML response, a deserializer, an outbound URL, a log line, a redirect.
4. **Control** — is there something between source and sink that makes the sink safe *for this kind of sink*? Escaping HTML does nothing for a SQL query.

Start from sinks when the codebase is large (search for the dangerous calls listed per category, then walk backwards to see whether untrusted data can reach them). Start from entry points when it is small enough to read.

Spend the manual effort where scanners are weakest: **authorization** (may *this* user act on *this* object?), **business logic** (can steps be skipped, repeated, or raced; can a price, quantity, or role be supplied by the client?), **cryptography used wrongly**, and **what happens on the error path**.

### Step 4 — Verify every candidate

For each lead from Steps 2 and 3, answer these before it becomes a finding:

- **Is the source really attacker-controlled?** A value from a config file the deployer writes is not the same as a query parameter.
- **Is the sink reachable?** Dead code, test fixtures, example scripts, and build tooling are lower stakes; say so rather than rating them like production paths.
- **Is there a control you missed?** Check upstream middleware, framework defaults, a wrapper function, a schema validator. Read it; don't assume from its name.
- **Does the context make it harmless?** MD5 as a cache key is fine; MD5 for a password is not. `eval` on a constant is odd; `eval` on request data is critical.

Then give each one a status:

- `confirmed` — you read the whole path from source to sink and found no effective control.
- `likely` — the path is visible but something on it couldn't be resolved from the code (dynamic dispatch, config not in the repo).
- `needs runtime check` — depends on deployment or behavior the code doesn't settle (is this port exposed? does the proxy strip this header?).

Drop everything else, and keep a one-line list of what was dropped and why — it shows the user what was checked and saves them re-raising it.

### Step 5 — Rate severity

Rate each finding with the [severity rubric](owasp-checks.md#severity-rubric): how easily it can be reached, and what an attacker gets. State both in one clause ("anonymous, one request; all customer records"). Attach the CWE id and the cheat sheet that covers the fix.

Don't inflate. If everything is High, nothing is, and the one finding that needs action tonight is buried.

### Step 6 — Report

**Lead with anything urgent.** A confirmed Critical — a live-looking secret in the repo, anonymous access to sensitive data, code execution from a request — goes at the very top, in plain words, before any table.

Then the report, using the [report template](owasp-checks.md#report-template):

- **Summary**: what was scanned (mode, commit, paths), tools run, counts by severity, and an overall read in two sentences.
- **Findings table**, most severe first:

  | # | Severity | Finding | Location | Status | CWE |
  |---|----------|---------|----------|--------|-----|

- **Per finding**: what the flaw is, how untrusted input reaches it, what an attacker gains, the specific fix for this codebase (name the function, the library call, the config key), how to verify the fix (ideally a test in which the malicious input is rejected), and the cheat sheet reference.
- **Not covered**: categories skipped and why, anything that needs a runtime or infrastructure review, and the plain statement that a code scan with no findings in an area is not proof the area is secure. This is not a penetration test or a compliance audit.

Save it to `docs/architecture/security-scan.md` unless the user names another place or the repository is public (see the rules of engagement), with the commit it was run against. In chat, give the urgent items, the table, and the path to the file.

### Step 7 — Let the user choose what to fix

Offer the findings as selectable options with `AskUserQuestion`, `multiSelect: true`, grouped by severity. The tool holds at most 4 questions of 4 options, with labels of a few words: label each option with its number and a short name (`#2 SQL injection in search`), put location and severity in the description, and say that other findings can be added by number through "Other". If the tool isn't available (a non-interactive run), print the table and ask for a list of numbers.

For the selected findings, produce a fix plan, most severe first:

- The change, at file/function level, using the fix from the cheat sheet that fits the stack (parameterized query, allow-list, the framework's own escaping) and not a hand-rolled filter.
- A **regression test** per fix that sends the malicious input and asserts it is refused. A security fix without a test tends to come undone in a later refactor.
- For a leaked secret: **rotate it first**, then remove it from the code; removing it does not un-leak it, and it remains in git history until that is rewritten.
- For a fix that tightens access or validation: note which legitimate callers might break, and whether a log-only stage is possible first.
- Fix the **class**, not only the instance: if one query is string-built, search for the others; if one route lacks the check, move the check to where no route can skip it. That structural change is [[sw-architecture-reviewer]] territory — say so when it applies.

Implement the fixes only if the user asks for that; otherwise the plan is the deliverable. Unselected findings stay in the report with status "open".

## Anti-patterns to avoid

- **Pattern matching without tracing.** "Found `exec(`" is a search result. Whether request data can reach it is the finding.
- **Scanner output as a report.** Unverified tool hits, duplicated per line, with no reachability check, are noise.
- **Severity inflation.** Rating a missing security header the same as an injectable query teaches the reader to ignore the ratings.
- **Checking what doesn't apply.** XSS advice for a service that emits no HTML, CSRF for a token-authenticated API with no cookies. Say it's out of scope and move on.
- **Stopping at injection.** The classics are easy to spot. Broken authorization and business-logic flaws are more common in practice and need you to understand what the code is *for*.
- **Reproducing secrets or writing exploits.** The report should help the defender and be useless as a toolkit.
- **Touching live systems or using found credentials.** A scan reads code.
- **Fixing mid-scan.** Changing code before the user has seen the findings hides what was wrong and skips their choice.
- **A clean bill of health.** No scan proves absence. Always say what was not covered.

After drafting, run through the [self-review checklist](owasp-checks.md#self-review-checklist).
