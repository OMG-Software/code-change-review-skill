# Verifying Findings

Read this before reporting any finding. Most false positives are not invented bugs. They are real-looking bugs that rest on one fact the reviewer assumed instead of checking: a type inferred from how it's used at other call sites, a function assumed to skip a guard because its name doesn't mention one, a call assumed dead because the diff doesn't show a caller. The fix is depth: settle every fact the finding depends on by reading or running something, before writing the comment.

## Contents

- The procedure (load-bearing facts, settle each, argue against it, grade)
- How deep to go (what counts as settled)
- False positive patterns and the check that catches each
- Independent verification
- Posting without a human in the loop

---

## The procedure

### 1. List the load-bearing facts

Write the finding as a chain: *this input or state* reaches *this code*, which *does or fails to do X*, so *this goes wrong*. Every link is a fact. A fact is load-bearing if the finding falls apart when it is false. Typical ones:

- **What a thing is:** the type of a field, what a function returns, whether a value can be null, which overload or implementation runs.
- **What a thing does:** whether a callee validates, copies, escapes, locks, retries, frees or owns.
- **Reachability:** who calls this, with what input, under what config or flag. Is the input really untrusted at this point?
- **Absence:** "never checked", "no caller", "no test", "not handled". Absence is the hardest to prove and the most often wrong.
- **External rules:** what the language, library version, protocol or spec says.
- **Intent:** whether the project decided this on purpose (ADR, design doc, comment, linked issue).

### 2. Settle each fact by reading or running something

A fact is settled only when you can point at the line, doc or output that establishes it. A name, an idiom, how other call sites use the thing, or what would be "the likely design" settles nothing.

- **Open the definition** of every type, function, macro and config key the finding names. Follow it until the fact is settled, through wrappers, overloads, base classes and generated code, not just one hop.
- **Trace upstream** to where the data comes from. Look for validation, normalization or a guard on the way, including in callers outside the diff.
- **Trace downstream** to where the data ends up. Does the dangerous sink actually receive it, or does an escape, copy or check sit in between?
- **Read the counterpart.** A serializer has a deserializer, a writer has a reader, a lock has an unlock, a migration has its down step, a producer has a consumer. A bug "in" one half is often handled in the other.
- **Search before claiming absence.** Search the whole repository, not only the diff, for callers, tests, handlers and checks, including registration tables, reflection, routes, build targets, other languages and the rest of the same change. Say what you searched for.
- **Check external rules at the source.** For language semantics, recall the exact rule, not the gist (see the patterns below). For a library, read the version the lockfile pins: the vendored or installed source, or its docs for that version. For a spec or RFC, find the section. If you can't check it, it is not settled.
- **Read the project's decision records** when the finding goes against something that looks deliberate: ADRs, `docs/`, architecture notes, comments next to the code, the PR description. A documented trade-off is not a defect. You may still disagree with it, but say so as a question about the decision, citing it, not as a bug.
- **Run it** when that is cheap and safe: a unit test, a small program under a sanitizer, a REPL, the type checker. A reproduction beats any amount of reading.

### 3. Argue against it

Before writing the comment, make the strongest case that the finding is wrong, then check that case too.

- What would the author say? "That's validated in X", "that's intended per Y", "that can't happen because Z". Go and look at X, Y and Z.
- **Evidence against the finding counts against it.** If the tests pass, the code has run in production, or the scenario needs an unusual input, treat that as a reason to doubt the finding. Don't invent an explanation for why the evidence doesn't apply ("the values are short enough to sit in the small-string buffer, so the tests pass anyway"). Explaining away evidence that contradicts you is the clearest sign of a false positive.
- Hedged wording in your own draft is a signal. "If", "likely", "probably", "may", "presumably" or "assuming" in the claim or the failure scenario marks a fact you haven't settled. Settle it, or drop the finding.

### 4. Grade, and decide

- **Confirmed:** every load-bearing fact is settled and you can cite where. Report it.
- **Plausible:** only for a fact that cannot be reached from where you are: production config or data, another service's behaviour, a runtime condition you can't reproduce. Name that fact in the comment ("Plausible: confirmed if the queue is shared across tenants in production"). **If you could check the deciding fact with the tools you have (read a file, grep, run a test), you must check it now. It is not Plausible.** Writing "confirmed if X" and posting without looking at X is the most common cause of a false positive.
- **Unsettled:** a load-bearing fact is still an assumption you could have checked but couldn't settle (for example, the code is too indirect to follow). Drop the finding, or, if being wrong would be costly, ask it as a question that names the specific fact: `[P2] MAJOR Can `user_id` be null when this is called from the webhook path?`, not a bug claim with a hedge.

## How deep to go

Depth follows severity and cost of error. Every finding needs each load-bearing fact settled, but:

- `[P1]`/`[P2]`: trace the whole path from source to sink, read the counterparts, and try to reproduce it. Blocking a merge on a wrong finding costs the author real time and costs the reviewer trust.
- `[P3]`: settle each fact by reading. A reproduction is optional.
- `[P4]`/`[P5]`: settle the facts the claim names (the duplicate helper really exists, the convention really is otherwise). These are cheap to verify and cheap to drop.

When the deciding fact is one search or one file away, depth is not optional at any severity.

## False positive patterns

Each pattern below is a real kind of rejected review comment, with the check that would have caught it.

| Pattern | What the reviewer assumed | The check |
|---|---|---|
| **Type inferred from use** | "Other call sites pass literals, so this field is probably a `string_view`." | Open the type's definition. |
| **Behaviour inferred from a name** | "`wire_callbacks` loads the signing key, so the worker loads it too." | Read the function body, including the guards that make it skip work (`if (override == nullptr)`). |
| **Half of a pair** | "The deserializer drops the `reason` field." | Read the serializer and deserializer together; check both sides of the wire. |
| **Language rule half-remembered** | "A temporary in the argument list dangles before the call reads it." | State the exact rule. In C++, temporaries live until the end of the full-expression, which includes the call; they dangle only when a reference or view outlives that expression (stored in a member, returned, captured by a deferred callback). |
| **Unused or dead code** | "No caller in the diff, so it's dead." | Search the whole repo and every build target, plus registration, routes, reflection and macros. Static analysers miss calls too; check before repeating their claim. |
| **Missing test** | "No test changed, so the behaviour is untested." | Search the test tree for the function, the endpoint and the scenario, including integration and conformance suites. |
| **Missing validation** | "The input reaches the query unchecked." | Trace upstream through every caller to the trust boundary; look for schema validation, middleware, typed parsing. |
| **Spec or standard misread** | "Users who left the room must not see later events." / "Use HTTPS, not HTTP." / "SHA-1 is weak." | Find the section of the spec or RFC. The protocol may require the behaviour (loopback HTTP redirect URIs, HMAC-SHA1 in a third-party API, `world_readable` visibility). |
| **Documented decision** | "This should block until the reload is confirmed." | Check ADRs, design docs and comments. If it is a recorded trade-off, either drop it or question the decision explicitly. |
| **Moved, not changed** | "This new constructor takes a large object by value." | Check whether the code is new or moved verbatim (`git diff -M`, `git log -L`, or the base version). Moved code is pre-existing; label it so or drop it. |
| **Fixed elsewhere in the change** | "The new column isn't added to the serializer." | Read the whole change set, not only the hunk; the other half is often in another file of the same PR. |
| **Process or metadata out of context** | "This version bump skips a number." | Check the project's process docs and other open PRs that may have taken the number. |
| **Library behaviour from memory** | "This function throws on empty input." | Read the pinned version's source or docs; behaviour changes between versions. |
| **Concurrency that can't happen** | "Two requests can race on this map." | Confirm the code runs concurrently: thread model, event loop, actor, per-request instance, lock held by the caller. |

## Independent verification

If you can start subagents, verify each `[P1]`–`[P3]` finding with one that hasn't seen your reasoning:

- Give it the claim, the file paths and line numbers, and how to read the code (the PR ref or branch). Don't give it your failure scenario or your confidence, so its read isn't anchored on yours.
- Ask it to **disprove** the finding: find the guard, the definition, the caller, the test, the spec section or the decision record that makes it wrong, and to return `holds`, `refuted` (with the citation) or `unsettled` (with the fact it couldn't settle).
- Drop `refuted` findings. For `unsettled`, settle the named fact yourself or apply the grading rules above.

Verify findings in parallel where the host allows it. Without subagents, do step 3 of the procedure as a separate pass after you have drafted every finding, so you are re-reading the code rather than your own reasoning.

## Posting without a human in the loop

When findings go straight onto a pull request (a review bot, a CI job), nobody filters them before the author sees them, so raise the bar:

- Post only Confirmed findings, plus Plausible `[P1]`/`[P2]` findings whose deciding fact is genuinely out of reach and named in the comment.
- Leave out Plausible `[P3]`–`[P5]` findings. If you want, list them in the review body as questions.
- Cite the lines that settle the load-bearing facts in **Why it matters**, so the author can check your reasoning in seconds instead of re-deriving it.
