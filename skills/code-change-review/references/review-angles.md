# Review Angles: Full Checklist

Language-agnostic. Pair it with the language files for the specific forms these issues take. You don't need to tick every box on every change. Spend time where the change carries risk.

## Contents

- Tier 1: Is it right? (correctness, intent, errors, concurrency, blast radius)
- Tier 2: Is it safe to ship? (security, compatibility, data, operability, dependencies, privacy)
- Tier 3: Is it good code? (performance, altitude, duplication, simplicity, consistency, readability)
- Tier 4: Is it verified? (tests, docs)
- Context-dependent angles (UI, cross-platform, cost)

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

### Intent fidelity
- Does the change do what the description says, *completely*? Look for missed call sites, a rename half done, a flag added but never read.
- Is there unrelated change mixed in? It may be accidental (debug code, commented-out blocks, changed defaults).
- Has existing behaviour been removed or changed without that being stated?

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
- Path traversal on any file path built from input. Input includes the command-line arguments and environment of tools that CI jobs or agents run, even when today's only caller is trusted: analysers such as SonarQube treat them as untrusted (`pythonsecurity:S8707`), and the project may already have its answer (resolve the path and require it to stay under a work folder, or take no path arguments at all). Follow that answer.
- Crypto: home-grown schemes, weak algorithms, non-constant-time comparison of secrets, predictable randomness.
- Output encoding: XSS where data reaches HTML or JS contexts.
- DoS vectors: unbounded input sizes, regex backtracking (ReDoS), unbounded loops or recursion on input.

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

### Dependencies
- Is the new dependency needed? Is it a large package pulled in for a small function?
- Maintained, reputable, license compatible? Typosquat check on the name.
- Pinned or locked appropriately; the lockfile updated consistently.
- Transitive weight and security advisories.

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
