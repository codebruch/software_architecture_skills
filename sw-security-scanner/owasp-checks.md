# Security checks

What to look for in each category, where to look, and what the fix is. The checks are drawn from the [OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/) (CC BY-SA 4.0); each section names the cheat sheets it rests on. Every sheet lives at `https://cheatsheetseries.owasp.org/cheatsheets/<Name>_Cheat_Sheet.html` with spaces as underscores — fetch the sheet when you need more detail than is here, or the stack-specific one from [the last section](#stack-specific-cheat-sheets).

Contents: [1 Access control](#1-access-control) · [2 Authentication and sessions](#2-authentication-and-sessions) · [3 Injection](#3-injection) · [4 Browser-facing output](#4-browser-facing-output) · [5 Files, paths, and parsers](#5-files-paths-and-parsers) · [6 Outbound requests](#6-outbound-requests) · [7 Cryptography and secrets](#7-cryptography-and-secrets) · [8 Errors, logging, and privacy](#8-errors-logging-and-privacy) · [9 Input validation and business logic](#9-input-validation-and-business-logic) · [10 API styles](#10-api-styles) · [11 Dependencies and supply chain](#11-dependencies-and-supply-chain) · [12 Configuration and deployment](#12-configuration-and-deployment) · [13 AI features](#13-ai-features) · [Scanners](#scanners-by-ecosystem) · [Severity](#severity-rubric) · [Report template](#report-template) · [Self-review](#self-review-checklist)

Only work through the sections that apply to the stack. Each has **search for** hints — starting points for finding sinks, not findings in themselves.

---

## 1. Access control

*Authorization, Insecure Direct Object Reference Prevention, Mass Assignment, Multi Tenant Security, Transaction Authorization, Cross-Site Request Forgery Prevention.*

The most common serious flaw, and the one scanners find least. Read each entry point and ask who may call it and on which objects.

**Look for:**
- Routes with no authentication or permission check — compare each handler against its neighbours; the odd one out is usually the bug. Admin, export, debug, and internal endpoints are the usual suspects.
- Object-level checks missing: a record loaded by an id from the request (`/orders/{id}`, `?user_id=`) with no check that it belongs to the caller or their tenant.
- Function-level checks missing: an action any logged-in user can call that only an admin should.
- Checks done only in the UI or only at a gateway, with the service trusting whatever arrives.
- Deny-by-default absent: each new route must remember to add the check, instead of the check applying unless a route opts out.
- Mass assignment: request bodies bound straight onto a model or passed as `**kwargs`/spread into an update, so a client can set `role`, `is_admin`, `price`, `owner_id`.
- Multi-tenant data where the tenant filter is each query's responsibility.
- State-changing requests authenticated by cookie with no CSRF token, no `SameSite` attribute, and no origin check. (Not applicable to APIs authenticated purely by a header token.)
- High-value actions (payment, email or password change, permission grant) with no re-authentication or confirmation step.

**Search for:** route/handler registrations; `get_by_id`, `findById`, `.get(id)`; `request.json` / `req.body` passed whole into create/update; `is_admin`, `role`; decorator or middleware lists per route.

**Fix:** enforce authorization server-side in one layer every request passes through, deny by default; check ownership/tenant in the data-access layer; bind request bodies through an explicit allow-list of fields.

---

## 2. Authentication and sessions

*Authentication, Session Management, Password Storage, Forgot Password, Multifactor Authentication, Credential Stuffing Prevention, JSON Web Token, OAuth2, SAML Security.*

**Look for:**
- **Password storage**: plaintext, reversible encryption, or a fast hash (MD5, SHA-1, SHA-256, with or without salt). Acceptable, in order of preference: Argon2id (at least 19 MiB memory, 2 iterations, parallelism 1), scrypt (N=2^17, r=8, p=1), PBKDF2-HMAC-SHA-256 with 600,000 iterations where FIPS is required, bcrypt (work factor ≥ 10, 72-byte input limit) for legacy systems. A unique random salt per password, which mature libraries handle.
- Home-grown authentication, token, or session code where the framework provides one.
- Hard-coded, default, or fallback credentials (`os.environ.get("TOKEN", "dev-token")` ships the default to production when the variable is unset).
- Secrets compared with `==` instead of a constant-time comparison.
- No rate limit, lockout, or delay on login, password reset, token verification, or MFA code entry.
- Login or reset responses that reveal whether an account exists.
- Password reset tokens that are guessable, long-lived, reusable, or not tied to the user; reset links built from the request's `Host` header.
- **Sessions**: session id not regenerated at login; no idle or absolute timeout; logout that doesn't invalidate server-side; session ids in URLs. Cookies missing `Secure`, `HttpOnly`, or `SameSite`.
- **JWT**: algorithm taken from the token (`alg: none`, or RS256/HS256 confusion); signature not verified (`decode` without `verify`); `exp`, `aud`, `iss` not checked; a weak or hard-coded signing secret; no way to revoke; sensitive data in the payload; tokens kept in `localStorage` in an app with any XSS exposure.
- **OAuth/OIDC**: missing or unchecked `state`; no PKCE for public clients; redirect URIs matched loosely; implicit flow; tokens in URLs or logs.

**Search for:** `md5`, `sha1`, `sha256(` near `password`; `jwt.decode`, `verify=False`, `algorithms=`; `set_cookie`, `session`; `==` near `token`/`secret`/`api_key`; `environ.get(` with a default on a secret.

---

## 3. Injection

*Injection Prevention, SQL Injection Prevention, Query Parameterization, NoSQL Security, OS Command Injection Defense, LDAP Injection Prevention, XPath Injection Prevention, Server Side Template Injection Prevention.*

Untrusted data that becomes part of a command for an interpreter.

**Look for:**
- **SQL** built by concatenation, f-strings, `%` or `.format`, including `ORDER BY`, table and column names, `LIMIT`, and `LIKE` patterns. ORMs are safe until their raw-query escape hatch is used.
- **NoSQL**: request objects passed directly as a query (`find(req.body)` lets a client send `{"$ne": null}`); `$where` with string-built JavaScript.
- **OS commands**: `shell=True`, `os.system`, `exec`, backticks, `Runtime.exec` with a single string, where any part comes from input. Arguments passed as a list are safer but an attacker-controlled value starting with `-` can still be read as an option.
- **Code evaluation**: `eval`, `exec`, `Function(...)`, `setTimeout(string)`, dynamic `import`/`require` on input.
- **Templates**: user input used *as* the template (`render_template_string(user_input)`), not merely passed into one.
- **LDAP / XPath / header / log / email-header** injection: input placed into a filter, expression, response header, log line, or mail header without encoding for that context.

**Search for:** `execute(` with `+`, `%`, `f"`; `raw(`, `.extra(`, `text(`; `subprocess`, `os.system`, `popen`, `child_process`, `exec(`, `eval(`; `render_template_string`, `Template(`; `$where`.

**Fix:** parameterized queries / prepared statements (bind values, never splice them); allow-list identifiers that can't be bound; call programs with an argument array and no shell, or use a library instead of a command; never evaluate input.

---

## 4. Browser-facing output

*Cross Site Scripting Prevention, DOM based XSS Prevention, Content Security Policy, HTTP Headers, CORS Security, Clickjacking Defense, Unvalidated Redirects and Forwards, Third Party Javascript Management, Prototype Pollution Prevention, HTML5 Security.* Skip this section for services that emit no HTML and are never called from a browser with credentials.

**Look for:**
- Untrusted data written into HTML without context-appropriate encoding; auto-escaping switched off (`|safe`, `mark_safe`, `{{{ }}}`, `dangerouslySetInnerHTML`, `v-html`, `innerHTML`, `document.write`).
- Data placed in a script block, an event-handler attribute, a URL (`href` allowing `javascript:`), or CSS, where HTML-escaping is the wrong encoding.
- DOM XSS: `location`, `document.referrer`, `postMessage` data, or URL fragments flowing into `innerHTML`, `eval`, or jQuery `$()`/`.html()`.
- `postMessage` handlers that don't check `event.origin`.
- Redirects to a URL taken from the request without an allow-list.
- **CORS**: `Access-Control-Allow-Origin` reflecting the request's `Origin`, or `*`, together with credentials; `null` origin allowed.
- Missing headers on HTML responses: Content-Security-Policy, `X-Content-Type-Options: nosniff`, `frame-ancestors`/`X-Frame-Options`, Strict-Transport-Security, a sensible `Referrer-Policy`. These are Low or Medium on their own — defence in depth, not the hole.
- Third-party scripts loaded without Subresource Integrity or from hosts the project doesn't control.
- Prototype pollution: recursive merge/`Object.assign` of request JSON into objects; keys like `__proto__` not rejected.

**Fix:** rely on the framework's contextual auto-escaping and don't bypass it; sanitize HTML that must be rich with a maintained sanitizer; allow-list redirect targets and CORS origins.

---

## 5. Files, paths, and parsers

*File Upload, Path Traversal Prevention, XML External Entity Prevention, XML Security, Deserialization.*

**Look for:**
- File paths built from input (`open(base + name)`, `sendFile(req.query.file)`) with no canonicalization and containment check — `../` and absolute paths escape the intended directory. Archive extraction that trusts entry names ("zip slip").
- **Uploads**: type decided by the client's filename or `Content-Type`; no size limit; stored under the web root or under the uploaded name; served back with a content type the browser will execute.
- **XML** parsed with external entities and DTDs enabled (many parsers' default): leads to file disclosure and SSRF.
- **Deserialization** of untrusted data with a format that can instantiate arbitrary types: Python `pickle`, `yaml.load` without a safe loader, Java native serialization, PHP `unserialize`, .NET `BinaryFormatter`, Ruby `Marshal`. This is frequently remote code execution.

**Search for:** `open(`, `sendFile`, `os.path.join` with request data; `pickle.loads`, `yaml.load(`, `ObjectInputStream`, `unserialize(`, `Marshal.load`; XML parser construction; `extractall`.

**Fix:** resolve the path and verify it is inside the allowed directory; generate storage names server-side and keep uploads outside the web root; disable DTDs and external entities; use data-only formats (JSON) or safe loaders.

---

## 6. Outbound requests

*Server Side Request Forgery Prevention, Webhook Security.*

**Look for:**
- The server fetching a URL, host, or path that comes from input (image/URL preview, webhook targets, import-from-URL, PDF rendering). An attacker points it at internal services or the cloud metadata address (`169.254.169.254`).
- Allow-lists checked against the string and not the resolved address; redirects followed; DNS re-resolved between check and use.
- **Incoming webhooks** accepted without verifying the sender's signature (constant-time), without a timestamp/replay check, or processed more than once on redelivery.
- **Outgoing webhooks** sent to user-supplied URLs with no SSRF protection, or carrying secrets in the URL.
- Outbound calls with no timeout (also a denial-of-service lever) or with TLS verification disabled (`verify=False`, `rejectUnauthorized: false`, `InsecureSkipVerify`).

**Search for:** `requests.get(`, `urlopen(`, `fetch(`, `http.Get(`, `axios` with a variable URL; `verify=False`.

**Fix:** allow-list destinations where possible; otherwise resolve, reject private/loopback/link-local ranges, and connect to the resolved address; verify webhook signatures over the raw body.

---

## 7. Cryptography and secrets

*Cryptographic Storage, Key Management, Secrets Management, Transport Layer Security, HTTP Strict Transport Security, Pinning.*

**Look for:**
- **Secrets in the repository**: API keys, passwords, private keys, connection strings, signing secrets in source, config, `.env` files committed by mistake, Dockerfiles, CI definitions, IaC, test fixtures, notebooks — and in git history. Cite location and kind; never the value.
- One secret shared across environments or components; no rotation path; secrets passed on command lines or baked into images.
- Broken or misused primitives: DES/3DES/RC4, ECB mode, static or reused IVs/nonces, encryption without authentication (CBC with no MAC — prefer an AEAD such as AES-GCM or ChaCha20-Poly1305), hard-coded keys, keys derived from a password with a plain hash.
- Non-cryptographic randomness (`random`, `Math.random`, `rand()`) for tokens, session ids, reset codes, or keys.
- Home-made cryptography or protocols.
- Sensitive data stored unencrypted where the threat model expects protection; data sent over plain HTTP; TLS certificate verification disabled; old protocol versions allowed.

**Search for:** `password =`, `secret`, `api_key`, `token`, `BEGIN PRIVATE KEY`, `AKIA`; `random.` / `Math.random` near `token`; `MODE_ECB`, `DES`, `MD5`; `verify=False`.

**Fix:** move secrets to a secret manager or injected environment and **rotate anything that was committed**; use the platform's CSPRNG (`secrets`, `crypto.randomBytes`); use a vetted high-level crypto library with authenticated encryption.

---

## 8. Errors, logging, and privacy

*Error Handling, Logging, Logging Vocabulary, User Privacy Protection.*

**Look for:**
- Stack traces, SQL errors, internal paths, or framework debug pages returned to clients; debug mode enabled in production configuration.
- Error paths that fail *open*: an exception in the permission check that lets the request through; a `catch` that swallows a verification failure.
- Secrets, tokens, passwords, card numbers, session ids, or personal data written to logs, traces, metrics labels, or analytics.
- Untrusted input written to logs unencoded (forged log lines).
- No log record for security-relevant events: login success and failure, permission denials, password and permission changes, admin actions, data exports.
- More personal data collected, returned, or retained than the feature needs.

**Search for:** `traceback`, `printStackTrace`, `DEBUG = True`; `print(`/`log` calls with request bodies, headers, or `password`/`card`/`token`.

**Fix:** generic error to the client, detail in the server log with a correlation id; redact at the logging layer; log security events with who, what, when, and outcome.

---

## 9. Input validation and business logic

*Input Validation, Business Logic Security, Abuse Case, Denial of Service, Bot Management and Anti-Automation, Email Validation and Verification.*

**Look for:**
- No validation at the boundary: type, length, range, and format unchecked; negative quantities and amounts; arithmetic on client-supplied prices or totals.
- Validation only on the client.
- Values the server should compute taken from the request: price, discount, user id, role, tenant.
- Workflow steps that can be skipped, repeated, or replayed (apply a coupon twice, refund more than was paid, confirm without paying).
- Race conditions on check-then-act sequences (balance check then debit, "is this code unused?" then use it) with no lock, transaction, or unique constraint.
- Unbounded work an attacker can trigger cheaply: no pagination limit, no body-size limit, regular expressions prone to catastrophic backtracking on input, expensive endpoints with no rate limit, unbounded in-memory growth per request.

**Fix:** validate against an allow-list schema at the boundary; recompute anything money- or permission-related on the server; make state transitions explicit and enforce them in a transaction; put limits on everything a client can make bigger.

---

## 10. API styles

*REST Security, REST Assessment, GraphQL, gRPC Security, WebSocket Security, Web Service Security, Microservices Security.*

- **REST**: every method on a resource is authorized, not only `GET`; responses don't return whole internal records; content type is validated; no sensitive data in URLs.
- **GraphQL**: introspection and field suggestions exposed in production; no depth, complexity, or batching limits; authorization on the top-level query but not on nested resolvers.
- **gRPC**: plaintext channels; no per-method authorization; reflection enabled in production; no message-size limits.
- **WebSocket**: no authentication at the handshake; `Origin` not checked (cross-site WebSocket hijacking); no authorization per message; no size or rate limits.
- **Service-to-service**: internal calls trusted because of where they come from; user identity not propagated, so the downstream service can't authorize.

---

## 11. Dependencies and supply chain

*Vulnerable Dependency Management, Software Supply Chain Security, NPM Security, Dependency Graph SBOM.*

**Look for:**
- Known-vulnerable versions — from the ecosystem's audit tool against the lockfile. Report the package, the fixed version, and whether the vulnerable code path is used where that is cheap to tell.
- No lockfile, or unpinned/floating versions and base images (`latest`), so builds aren't reproducible.
- Dependencies fetched from unexpected registries or by URL/git reference; names one typo away from a popular package; internal package names that could be claimed on a public registry.
- Install-time scripts running unreviewed; abandoned packages on a critical path.

Don't guess at CVEs from memory. If no audit tool can be run, say the dependency check was not performed and name the command that would do it.

---

## 12. Configuration and deployment

*Docker Security, Kubernetes Security, Infrastructure as Code Security, CI CD Security, GitHub Actions Security, Serverless FaaS Security, Secure Cloud Architecture, Database Security.* Check whatever of these is in the repository.

- **Application config**: debug mode on; default credentials; permissive defaults that production inherits; admin/debug/metrics endpoints on the public listener; services bound to `0.0.0.0` that should be internal.
- **Containers**: running as root; secrets in `ENV`, `ARG`, or image layers; unpinned base images; the Docker socket or host paths mounted; unnecessary capabilities or `--privileged`.
- **Kubernetes**: privileged pods, `hostNetwork`/`hostPath`, no resource limits, no network policies, secrets in plain manifests, over-broad RBAC.
- **IaC / cloud**: public storage buckets, security groups open to `0.0.0.0/0` on admin or database ports, wildcard IAM policies, unencrypted storage, state files with secrets committed.
- **CI/CD**: secrets echoed to logs; workflows that run untrusted pull-request code with secrets available (`pull_request_target`); third-party actions pinned to a mutable tag and not a commit SHA; untrusted input (branch name, PR title) interpolated into `run:` scripts; over-broad token permissions.
- **Database**: the application connecting as an owner/superuser; no TLS to the database; the database reachable from the internet.

---

## 13. AI features

*LLM Prompt Injection Prevention, AI Agent Security, MCP Security, RAG Security.* Only when the codebase calls a language model.

- Untrusted content (user text, web pages, documents, tool results) placed in a prompt with authority to trigger tools, with no separation from instructions.
- Model output used unsanitized in a sink from sections 3–6 (rendered as HTML, run as a command, used as a query or URL). Treat model output as untrusted input.
- Agents or tools holding broader permissions than the task needs; destructive or outbound actions with no confirmation step.
- Retrieval that ignores the asking user's permissions, so a model can surface documents the user couldn't open directly.
- Secrets or other users' data included in prompts or logged with them.

---

## Stack-specific cheat sheets

When the stack matches, fetch the sheet for framework-specific defaults and pitfalls: Django Security, Django REST Framework, FastAPI Security, Laravel, Ruby on Rails, Symfony, Nodejs Security, NPM Security, Nextjs Security, JavaScript and TypeScript Security, DotNet Security, Java Security, Injection Prevention in Java, Bean Validation, PHP Configuration, NodeJS Docker, Mobile Application Security. The method itself follows the Secure Code Review and Attack Surface Analysis sheets.

---

## Scanners by ecosystem

Run what is installed; don't install without asking. Output is a list of leads for Step 4.

| Purpose | Tools |
|---------|-------|
| Secrets (tree and git history) | `gitleaks detect`, `trufflehog git file://.`, `detect-secrets`; fallback: `git log -p -S<pattern>` and targeted `git grep` |
| Dependencies | `npm audit` / `pnpm audit` / `yarn npm audit`, `pip-audit`, `govulncheck ./...`, `cargo audit`, `bundle audit`, `dotnet list package --vulnerable`, `mvn org.owasp:dependency-check-maven:check`; `osv-scanner` across ecosystems |
| Static analysis | `semgrep` (multi-language), `bandit` (Python), `gosec` (Go), `brakeman` (Rails), `eslint` with a security plugin (JS/TS), `spotbugs` + FindSecBugs (JVM), CodeQL |
| Containers / IaC | `trivy`, `hadolint`, `checkov`, `tfsec`, `kube-linter` |
| CI workflows | `actionlint`, `zizmor` |

Note in the report which tools ran, which weren't available, and what that leaves unchecked.

---

## Severity rubric

Severity comes from two questions: how easily can an attacker reach it, and what do they get? State both for every finding.

| Severity | When to assign | Examples |
|----------|----------------|----------|
| **Critical** | Reachable without authentication (or by any user), with little skill, and yields code execution, full data access, authentication bypass, or a working credential for something valuable. | SQL injection on a public endpoint; deserialization of request data; an unauthenticated admin or export endpoint; a production secret committed to the repo. |
| **High** | Serious impact but needs an account, a specific condition, or a second step; or easy to reach with impact limited to some users' data. | Missing object-level check (any user reads any other user's records); stored XSS; SSRF to internal services; passwords stored with a fast hash; JWT signature not verified. |
| **Medium** | Real weakness with limited impact, or one that needs unusual conditions or user interaction. | Reflected XSS behind a login; CSRF on a non-critical action; verbose errors exposing internals; no rate limit on login; sensitive data in logs. |
| **Low** | Defence-in-depth gaps and hardening with no direct path to harm on their own. | Missing security headers; cookie flags on a non-session cookie; non-constant-time comparison of a long random token; container running as root. |
| **Informational** | Worth knowing, not a vulnerability. | An outdated dependency with no known issue; a risky pattern that is currently unreachable. |

Adjust for context and say that you did: the same flaw is lower in an internal build script than in the request path, and higher where the data is payment or health data. Status (`confirmed` / `likely` / `needs runtime check`) is separate from severity — a `likely` Critical is still listed first, with what would settle it.

---

## Report template

```markdown
# Security scan — <project>

- **Commit:** <sha> (<date>)   **Mode:** baseline | diff <base>...<head>
- **Scope:** <paths / services>
- **Tools run:** <tool: result count> … **Not available:** <tools>
- **Findings:** <n> Critical, <n> High, <n> Medium, <n> Low, <n> Informational
- **Overall:** <two sentences>

## Act on these first
<Confirmed Criticals in plain words, with the immediate step — e.g. rotate the key.>

## Attack surface
| Entry point | Reachable by | Protected by |

## Findings
| # | Severity | Finding | Location | Status | CWE |

### #1 <title> — <severity>
- **Location:** file:line
- **What is wrong:** …
- **How it is reached:** <source → path → sink, and the condition; no payload>
- **Impact:** <what an attacker gains>
- **Fix:** <the specific change in this codebase>
- **Verify the fix:** <test or check>
- **Reference:** <cheat sheet name + URL>, CWE-<id>
- **Status:** open

## Checked and dismissed
<one line each: what looked suspicious and why it is not a finding>

## Not covered
<skipped categories and why; what needs runtime or infrastructure review; tools that could not run>
```

---

## Self-review checklist

Run through this before handing over the report.

### Conduct
- [ ] Nothing was sent to a deployed or shared system, and no discovered credential was used or tested.
- [ ] No secret value appears in the chat, the report, or any command; secrets are cited by location and kind.
- [ ] No working exploit or payload was written; each finding explains the path and condition only.
- [ ] No source file was modified during the scan.
- [ ] The report's location was checked against the repository's visibility.

### Coverage
- [ ] The attack-surface table lists every entry point with who can reach it and what protects it.
- [ ] Each applicable category was worked through; skipped categories are named with the reason.
- [ ] Access control and business logic were reviewed by reading the code, not left to scanners.
- [ ] Secrets were looked for in git history as well as the working tree, or the report says they weren't.
- [ ] Dependencies were audited with a tool, or the report says the check was not performed.

### Signal
- [ ] Every finding was traced from an attacker-controlled source to a sink, and upstream controls were read, not assumed.
- [ ] Every finding has a status: confirmed, likely, or needs runtime check.
- [ ] Scanner hits were verified individually; none were pasted in unverified.
- [ ] Dismissed leads are listed with the reason.
- [ ] Severities vary with reachability and impact, each with its one-clause justification; hardening items are not rated like exploitable flaws.

### Usefulness
- [ ] Confirmed Criticals are stated first, with the immediate action.
- [ ] Each fix names the specific change for this codebase and how to verify it.
- [ ] Leaked secrets come with "rotate", not just "remove".
- [ ] Where one instance points to a class of bug, the other instances were searched for.
- [ ] "Not covered" says plainly that this is not a penetration test and that no findings is not proof of security.
- [ ] The user chose which findings to fix before any plan or code change.
