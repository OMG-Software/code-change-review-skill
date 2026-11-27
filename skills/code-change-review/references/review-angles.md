# Review Angles: Full Checklist

Language-agnostic. Pair it with the language files for the specific forms these issues take. You don't need to tick every box on every change. Spend time where the change carries risk.

## Contents

- Tier 1: Is it right? (correctness, numbers and units, time, intent, errors, concurrency, messages and events, blast radius)
- Tier 2: Is it safe to ship? (security, cache isolation, compatibility, data, operability, load and shutdown, dependencies and copied code, privacy)
- Tier 3: Is it good code? (performance, altitude, new interfaces, duplication, simplicity, consistency, generated files, readability)
- Tier 4: Is it verified? (tests, weakened verification, docs)
- Context-dependent angles (UI, cross-platform, cost, mobile, code that calls a model, data and ML pipelines)

---

## Tier 1: Is it right?

### Correctness and logic
- Boundaries: empty, single element, max size, zero, negative, overflow, NaN, unicode and multi-byte strings, time zones, DST, leap days.
- Off-by-one in loops, slices, ranges and pagination (inclusive versus exclusive).
- Inverted or incomplete conditionals. Check `&&`/`||` precedence and De Morgan errors.
- Null, undefined or missing values on every new path, including optional fields from external input.
- Equality semantics: reference versus value, float comparison, case sensitivity, locale.
- State machines: every transition handled, no unreachable or stuck states.
- Copy/paste slips: a variable reused from the block above when it should be the new one.
- Determinism, where the output must be reproducible: a generated file that is checked in or compared with a fresh build, a build artifact, a cache key or content hash, a snapshot. Such output must not depend on hash-map or set iteration order, directory listing order, the current time or an unseeded random source. A generator that ranges over a map produces a different file on each run, so "is the generated file up to date?" checks fail at random and every regeneration shows churn. Randomness the output exists to have (keys, salts, nonces, tokens, randomized signatures) is exempt; removing it is the defect.

### Numbers, units and money
- Money in binary floating point (`float`, `double`, JS `number` used for amounts that are summed or compared). Check the type the project uses for money (integer minor units, `Decimal`, a money type) and that the new code keeps to it end to end, including parsing and serialization.
- Rounding: the mode (half-up, half-even, truncation) and *where* it happens. Rounding each line item and then summing gives a different total from summing and then rounding; tax, splits and currency conversion must follow the rule the domain sets.
- Unit mismatches at every boundary: cents versus whole units, ms versus s versus ns, bytes versus KiB versus KB, degrees versus radians. Read the callee's definition or the config key's documentation for the unit; a bare `timeout=30` or `amount=1999` says nothing.
- Currency: amounts in different currencies added or compared, or a currency's minor-unit count assumed to be 2 (JPY has 0, BHD has 3).
- Precision across boundaries: 64-bit integers (IDs, nanosecond timestamps) sent as JSON numbers to JavaScript lose precision above 2^53; a narrower column, field or type truncates.
- Integer division where a fraction was meant; percentages stored as 0–1 in one place and 0–100 in another.

### Time and clocks
- Durations, timeouts and rate limits measured with the wall clock (`time.time()`, `Date.now()`, `System.currentTimeMillis()`), which jumps when NTP or an operator corrects it. Elapsed time needs a monotonic clock.
- Clock skew between machines: an expiry, lease or token-validity check that compares a timestamp written by one host with the clock of another needs a tolerance, or a single source of time.
- Expiry boundaries: `<` versus `<=` on "expires at", TTLs computed in one unit and compared in another, a token checked as valid and then used after it expired.
- Stored timestamps without a time zone, or converted to local time before storage; schedules ("every day at 02:00") across DST changes.

### Intent fidelity
- Does the change do what the description says, *completely*? Look for missed call sites, a rename half done, a flag added but never read.
- Is there unrelated change mixed in? It may be accidental (debug code, commented-out blocks, changed defaults).
- Has existing behaviour been removed or changed without that being stated?
- Scope with a concrete cost: report a change that bundles parts which must deploy or roll back separately (a destructive migration with an unrelated feature, a risky behaviour change inside a large mechanical refactor that hides it from review), as a `[P4] MINOR (Quality)` finding naming that cost. Size alone, or a different way of splitting the work, is not a finding.

### Error handling and failure modes
- Swallowed errors (empty catch, ignored return codes, `_ =` discards).
- Fail-open versus fail-closed: on error, does an auth or permission check deny?
- Partial failure: if step 2 of 3 fails, is state consistent? Is there cleanup or a rollback?
- External calls: timeouts set? Retries bounded, with backoff? Are retried operations idempotent?
- Error messages: useful to the operator, safe for the end user (no stack traces or internals), and right for every case that reaches them. Advice written for one caller ("create the file, then extend it with edits") misleads when a different tool or input lands on the same message.
- Fallbacks obey the limits they enforce: a refusal, placeholder or truncated result must itself fit the configured cap at the smallest supported setting, or the fallback fails exactly where it was meant to recover.
- Resource cleanup on *every* path, including error paths (files, sockets, locks, transactions).

### Concurrency and state
- Check-then-act races (exists → create, read → modify → write without a lock or CAS).
- Shared mutable state across threads, requests, goroutines or async tasks.
- Lock ordering (deadlock), locks held across I/O or awaits.
- Async ordering assumptions: un-awaited promises or tasks, fire-and-forget that loses errors.
- Caches: invalidation on write, stampede, stale reads after update.

### Messages, events and distributed state
- Delivery semantics: most queues, streams and webhooks deliver *at least once*. A consumer that charges, emails, increments or inserts on each message must be idempotent: dedupe by a message or idempotency key, or make the write conditional. Settle which semantics apply from the broker client's configuration (acknowledgement mode, auto-commit, redelivery on timeout), not from the queue's name.
- Ordering: are messages for one entity guaranteed to arrive in order (partition key, FIFO group)? A consumer that applies "updated" after "deleted", or an older version over a newer one, needs a version or sequence check.
- Dual writes: writing to the database and publishing an event (or calling another service) as two steps loses one of them when the process dies in between. Look for an outbox, a transaction that covers both, or a reconciliation job.
- Acknowledge after the work, not before; a handler that acks first and then fails loses the message, and one that never acks on a poison message blocks the queue. Is there a dead-letter path and a retry limit?
- Idempotency keys on incoming requests that clients retry (payments, order creation): is the key stored and checked atomically with the effect, and scoped to the caller?
- Sagas and multi-service workflows: is there a compensating step for each forward step, and is it safe to run twice?

### Blast radius
- Every caller of a changed signature, behaviour, default or return value. Find them; don't assume.
- Changed defaults: who relied on the old one?
- Shared code (utils, base classes, middleware): the change applies to every consumer, not only the one the author had in mind.
- Sibling implementations: where several implementations take the same input (provider adapters, storage backends, platform ports, parsers for two wire formats), follow the unusual input the change is about (malformed, oversized, empty, an object where a string belongs) through each one. They should reach the same outcome, or the difference should be stated. A rule added in one adapter often leaves another rejecting, or accepting, that input before the new rule runs.

## Tier 2: Is it safe to ship?

### Security
- Injection: SQL, shell, LDAP, template, header, log and path, wherever untrusted data meets an interpreter.
- AuthN/AuthZ: is the check present on *every* new endpoint or action? Object-level authorization, not only "logged in"?
- Trust boundaries: is client-supplied data trusted for prices, roles, IDs or redirects?
- Secrets: hard-coded keys, secrets in logs, errors or URLs, overly broad tokens.
- Unsafe deserialization, XXE, SSRF (user-controlled URLs fetched server-side), open redirects.
- Path traversal on any file path built from input. The command-line arguments and environment of a tool that CI jobs or agents run count as input in two cases. One is when they can carry less-trusted data: a workflow input a PR controls, or a command an agent builds from PR content. The other is when the project enforces an analyser that flags them, such as SonarQube's `pythonsecurity:S8707`; the gate rule in `reporting.md` then ranks the finding. In either case, follow the answer the project already uses: resolve the path and require it to stay under a work folder, or take no path arguments at all. Otherwise, a path argument from a trusted caller is not a finding.
- Crypto: home-grown schemes, weak algorithms, non-constant-time comparison of secrets, predictable randomness.
- Output encoding: XSS where data reaches HTML or JS contexts.
- DoS vectors: unbounded input sizes, regex backtracking (ReDoS), unbounded loops or recursion on input.
- Web request baseline, in any language or framework. The language files list the framework-specific forms; these apply even where no language file names them:
  - CSRF: a state-changing endpoint that authenticates by cookie needs a CSRF token or an `Origin`/`Referer` check. A `SameSite` session cookie narrows the exposure but is not enough alone: `Lax` still sends the cookie on a cross-site top-level `GET`, so a state-changing `GET` stays exposed, and under either `Lax` or `Strict` a page on a sibling subdomain counts as same-site and gets the cookie. Endpoints that take only a bearer token from a header are not exposed.
  - CORS: a reflected `Origin` or a wildcard combined with credentials; an allow-list matched by substring or suffix (`evil-example.com` passing a check for `example.com`).
  - Cookies: session cookies set without `Secure`, `HttpOnly` and a `SameSite` value; session ID not rotated on login or privilege change (fixation).
  - Mass assignment: a request body bound straight onto a model so that a client can set `role`, `owner_id` or `price`.
  - Security headers the project sets elsewhere (CSP, `X-Content-Type-Options`, frame protection) missing from a new route or a new server.
  - Rate limiting on login, password reset, OTP and other guessable endpoints.

### Cache and response isolation
- Every cache key must include each input that changes the result: user, tenant, role or permission set, locale, feature flags, API version. A key built from the path alone serves one user's data to the next. Read the key builder, not the variable name.
- HTTP caching: an authenticated or personalised response must not be cacheable by shared caches (`Cache-Control: private` or `no-store`, `Vary` on the right headers). A CDN rule or `public, max-age` added to a route that reads the session leaks responses across users.
- Multi-tenant data: queries, object storage paths, search indexes, background jobs and logs scoped by tenant on every new path, including jobs that run without a request context.
- Memoization or module-level caches in a server process outlive the request; check they are not keyed only by arguments that are the same for every user.

### Contracts and compatibility
- Public API, CLI flags, config keys, environment variables, event and message schemas, file formats: is the change backward compatible?
- Serialized data at rest: can the new code read old data, and can old code (during a rollout or downgrade) read new data? Check the largest record the new code can write once encoded (escaping, multi-byte characters, framing), not a typical one: a raised size limit can produce records an older reader or another service rejects.
- Enum or union additions: do consumers handle unknown values?
- Semver: does the change match the version bump?

### Data integrity and migrations
- Reversible? Is there a down migration, or a documented forward-only plan?
- Locking: will `ALTER`/index creation lock a hot table? Is it batched?
- Mixed-version window: the old app running against the new schema, and the reverse.
- Backfills: idempotent, resumable, throttled?
- Constraints: is uniqueness or foreign-key integrity enforced in the DB, or only in app code (which races)?

### Operability
- Can it be turned off (feature flag) or rolled back cleanly?
- Observability: logs at the right level, metrics or traces on the new path, enough context to debug an incident.
- Logs don't leak PII or secrets, and aren't so noisy that they bury signal or cost money.
- Config: new settings documented, safe defaults, validated at startup.
- Deploy ordering: does this need a migration, infra change or another service deployed first?

### Load, cancellation and shutdown
- Unbounded concurrency: fan-out over a list from input (`Promise.all`, a goroutine or task per item, a thread per request) without a semaphore, worker pool or batch size. One large request then exhausts connections, file descriptors or a downstream rate limit.
- Retry amplification: retries at several layers multiply (3 at the client × 3 at the gateway × 3 at the service = 27 calls per failure). Retries without jitter synchronise into waves after an outage.
- Backpressure: a producer that can outrun its consumer needs a bounded queue and a decision for when it is full (block, drop, shed with a clear error), not an in-memory buffer that grows until the process dies.
- Degradation: when an optional dependency (recommendations, analytics, a feature-flag service) is down or slow, does the main path still work, with a short timeout and a fallback, or does it fail or hang with it? A circuit breaker or fallback should exist where the project uses them for similar calls.
- Cancellation: when the caller gives up (request cancelled, deadline passed), is the cancellation passed down to queries and outbound calls, or does work continue for a client that has gone?
- Graceful shutdown: on SIGTERM or a rolling deploy, does the process stop accepting work, finish or hand back in-flight work, and flush buffers within the platform's grace period? New background loops, consumers and timers need to join that shutdown.
- Resource pools: connections or handles taken inside a loop or held across a slow call can exhaust the pool; check the pool size against the new concurrency.

### Dependencies and copied code
- Is the new dependency needed? Is it a large package pulled in for a small function?
- Maintained, reputable, license compatible? Typosquat check on the name.
- Pinned or locked appropriately; the lockfile updated consistently.
- Transitive weight and security advisories.
- Copied or vendored code: a file pasted from another project, a gist or an answer site carries that source's licence. Check its header or origin against the project's licence and how the project is distributed (a copyleft file in a permissively licensed library that others ship). Vendored code also needs its licence text and attribution kept, and a note of where it came from and which version, so that its security fixes can be followed.

### Privacy and compliance
- New personal data collected, stored, logged or sent to third parties?
- Retention and deletion paths; data minimization.

## Tier 3: Is it good code?

### Performance and efficiency
- Algorithmic: nested loops over growing collections, repeated linear scans that should use a map or set.
- N+1 queries or calls in a loop; missing batching.
- Work in hot paths that could be hoisted, cached or done once.
- Unbounded growth: caches without eviction, lists that grow per request, unbounded queues.
- Blocking I/O on event loops or UI threads.
- Over-fetching (`SELECT *`, full objects when you need IDs), missing pagination.
- But: don't flag micro-optimizations in cold code. Only flag a real cost on a real path.

### Altitude
- Is the fix at the layer where the problem originates, or patching a symptom downstream?
- A special case added where the general mechanism should be fixed, or the general mechanism changed when a local fix would do.
- Logic placed in the wrong layer (business rules in controllers or UI, I/O in domain models).
- Workarounds for a bug in your own code that should be fixed at the source.

### New public interfaces
A new public function, endpoint, CLI flag, config key, event or file format becomes a compatibility promise the day it ships, so judge its shape now, while it is still cheap to change. Report only what has a concrete cost to callers.
- Easy to misuse: boolean or positional parameters whose meaning is invisible at the call site (`send(msg, true, false)`), two parameters of the same type that can be swapped silently, a unit-less number (`timeout: 30`).
- Unsafe defaults: the default should be the safe and common case (validation on, TLS verification on, a bounded page size), with the risky option named as such.
- Hard to extend without breaking: a bare array or scalar returned where a later field will be needed (paginated lists, error details), an enum with no room for an unknown value, an error reported only as a string a caller would have to parse.
- Inconsistent with the interface it sits beside: naming, pagination, error shape, ID format or time format that differs from the project's other endpoints or functions of the same kind.
- One-way doors: identifiers, URLs, wire field names and persisted formats that will be expensive to change once clients or data depend on them. A recorded decision settles these; an accidental choice in an otherwise small change is worth one question.

### Duplication and reuse
- Copy-paste within the diff.
- Reimplementation of a helper or utility that already exists in the repo or standard library (search before flagging).
- Parallel structures that will drift (two lists of the same thing that must stay in sync).

### Simplicity and over-engineering
- Abstractions with one implementation and no clear second coming.
- Configurability or extension points nobody asked for.
- Dead code, unused parameters, leftover debug code. Search the whole repository and every build target (including registration tables, routes, reflection and macros) before calling code dead; a static analyser's "unused" alert is a lead, not proof.
- The reverse: clever one-liners that should be boring and readable.

### Consistency
- Matches the codebase's established patterns for errors, logging, naming, file layout and dependency injection.
- Doesn't introduce a second way of doing something the codebase already does one way.
- Follows the rules that recent commits applied to sibling code, where their reason applies. A sibling changed "for Sonar Sxxxx" sets the rule for new code that the same analyser rule would flag. A sibling that dropped its file argument because it only ever reads one fixed file does not forbid a file argument in a tool that needs one: check the path the way the project does instead (`SKILL.md`, step 3).

### Generated and derived files
- Generated code edited by hand (a file headed "Code generated … DO NOT EDIT", protobuf or OpenAPI output, an ORM's migration snapshot): the next regeneration silently drops the edit. The fix goes in the source or the generator.
- Source changed but the generated output not regenerated, or regenerated with a different generator version from the one the project pins: the checked-in output no longer matches what the build or other services produce.
- Derived files that must move together: a lockfile and its manifest, a schema and its generated client, a translation catalogue and its source strings, a snapshot of a migration's model state. Check each pair the change touches on one side.

### Readability
- Names say what things are. Functions do one thing at one level of abstraction.
- Comments explain *why* (constraints, non-obvious decisions), not *what*.
- Magic numbers or strings named.

## Tier 4: Is it verified?

### Tests
- Does a test exercise the new or changed behaviour? Would it *fail* if the change were reverted? Search the whole test tree (unit, integration, conformance) for the function, endpoint or scenario before reporting a test as missing.
- Edge cases from tier 1 covered, not only the happy path.
- Over-mocking: the test mocks the very thing it should be testing.
- Persistence round trips: a test of replay, restore, resume or migration must reload from storage (close and reopen, restart, a fresh reader) before it asserts. Reusing the object that did the writing passes even when nothing, or the wrong thing, was written.
- Flakiness sources: time, randomness, ordering, network, shared global state, sleeps.
- Test names describe behaviour; assertions are specific (not just "no exception").
- Bug fixes come with a regression test.

### Weakened verification
The change can make the existing safety net weaker as well as adding to it. Check every edit to tests, test config and CI in the change set, not only new tests:
- Tests deleted, skipped (`skip`, `xfail`, `@Disabled`, `t.Skip`, `it.skip`, `#[ignore]`) or commented out. Deleting a test whose subject the change also deletes is fine; deleting or skipping a test of behaviour that still exists, especially one that was failing, hides a regression.
- Assertions loosened: an exact value replaced by "not null", "contains" or a wider tolerance; an expected error removed; an `assert` turned into a log line.
- Expected values rewritten to match new output: snapshot and golden files regenerated wholesale, or expected numbers edited, in a change that does not mean to change that behaviour. Each changed expectation needs a reason the intent covers.
- Flakiness hidden rather than fixed: retries, longer sleeps or `rerun` markers added to a test that sometimes fails, without finding why.
- CI and tool config: `continue-on-error`, `|| true`, `allow_failure`, a check removed from the required list, a coverage or lint threshold lowered, a rule disabled, files added to an exclude list, a type checker relaxed (`strict` off, a new blanket `ignore`).
- Mocks widened so the test no longer touches the code under change.

### Documentation
- README, API docs, changelog and migration notes updated for user-visible changes.
- Comments and docstrings near edited lines still true.
- **Every factual claim the change adds or edits is true.** Prose in docs, ADRs, changelogs, runbooks and agent files (`AGENTS.md`, `CLAUDE.md`) states a contract: error and status codes, limits and sizes, file names and paths, config keys, defaults, preconditions, which cases succeed and which fail. List the concrete claims in each changed paragraph and check each one against the code or decision record it describes, at the layer it describes (`verification.md`, "Doc claim checked at the wrong layer"). Treat these docs as part of the code change, not as prose to skim.
- Recovery, upgrade and migration steps: walk them against the code. Does doing exactly what the doc says reach the promised state? A step that leaves out something the code also reads (rotated archives, a cache, a second config location) leaves the operator stuck while believing they followed the fix.
- Compatibility and limit claims hold at the boundary, not only in the typical case ("an older build can open it" must survive the largest record this build writes).
- Statements that must agree do: a changelog entry with its neighbours and the version bump, a summary (`README`, `AGENTS.md`) with the detailed doc, a doc with the ADR it cites. A summary that drops a condition is the version readers act on.

## Context-dependent angles

- **UI:** accessibility (labels, keyboard, contrast, focus), i18n and localization (hard-coded strings, pluralization, RTL), loading, empty and error states, responsive layout.
- **Cross-platform:** path separators, line endings, case-sensitive file systems, shell differences, locale and encoding defaults.
- **Cloud cost:** new always-on resources, per-request paid API calls, log or metric volume, egress.
- **Mobile:** battery, background execution limits, offline behaviour, app size.
- **Code that calls a language model:** (Instruction files that a model follows are covered by `languages/instructions.md`; this is application code that sends prompts and acts on replies.)
  - Prompt injection: untrusted content (web pages, emails, documents, tool output, user uploads) placed in a prompt for a model that can call tools or take actions. Is that content separated and marked as data, and are the tools it can reach limited to what the task needs, with confirmation for side effects?
  - Model output treated as trusted: executed as code or shell, run as SQL, rendered as HTML, used as a file path or URL, or parsed as JSON without validation against a schema. It needs the same handling as any other untrusted input.
  - Cost and limits: no maximum on output tokens, input size or tool-call loop iterations; a retry loop on a paid call; a large context sent on every request where caching or trimming applies.
  - Model identity: model IDs pinned to a specific version where behaviour must stay stable, and not hard-coded in several places.
  - Failure handling: refusals, truncated output (`max_tokens` reached), rate-limit and overload errors, and malformed structured output each have a defined path.
  - Tests that assert on exact model wording, or call the live API in unit tests, are flaky and cost money.
- **Data and ML pipelines:**
  - Training/serving skew: a feature computed one way where the model is trained and another where it is served (different missing-value fill, scaling, tokenizer, category mapping, time window). Both sides should call the same code or the same saved transform.
  - Schema drift: a pipeline step that reads columns by position, or silently drops, renames or retypes a column a downstream job reads.
  - Leakage: a feature built from data that would not be known at prediction time (future rows, the label itself, a split shuffled across time).
  - Silent data loss: joins that drop unmatched rows, `dropna` or filters that remove more than intended, with no row-count check or metric.
  - Reproducibility: unseeded randomness, unpinned data snapshots or model artifacts.
