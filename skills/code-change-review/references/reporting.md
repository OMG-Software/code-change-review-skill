# Reporting Findings

Every finding uses the same shape, whether it appears in a text report, a structured findings tool or a comment on a pull request. Readers learn the shape once and can triage at a glance.

## Severity tags

Severity is a priority rank from `[P1]` (most severe) to `[P5]` (least severe), always followed by its name. Rate impact times likelihood, not how interesting the finding is. Each finding starts with exactly one label.

| Label | Meaning | Examples |
|---|---|---|
| `[P1] CRITICAL` | Will cause serious harm in normal use, or is exploitable to cause serious harm. Block the merge. An exploit with limited impact is ranked by that impact, not raised to P1 because it is exploitable. | Auth bypass, SQL injection, data loss or corruption, crash on the main path, irreversible migration bug |
| `[P2] MAJOR` | Wrong behaviour that users or operators will hit, or a serious risk under realistic conditions. Fix before merging. | Race causing duplicate charges, unhandled error on a common path, breaking API change, N+1 on a hot endpoint |
| `[P3] MINOR (Defect)` | Wrong behaviour in edge cases or uncommon conditions, with limited impact. Fix in this change; need not block the merge. | Missing timeout, edge-case off-by-one, error swallowed on a rare path |
| `[P4] MINOR (Quality)` | No wrong behaviour today, but a real maintainability or operability cost, or a clear improvement with small impact. Fix when convenient. | Missing test for new logic that works, wrong-altitude fix, misleading log message, small duplication, avoidable complexity |
| `[P5] NIT` | Style or taste; no behavioural effect. In a report a person reads, count rather than list them unless there are no real defects or the user asked for a thorough pass. When a host sets the output, report them if its severity threshold reaches `[P5]` or it sets none. When you post to a pull request yourself, unattended and with no threshold configured, leave them out (`references/verification.md`). | Formatting the linter missed, naming, wording |

`[P1]` and `[P2]` block the merge; `[P3]` to `[P5]` do not.

A change that fails a gate the project enforces or keeps green (a required check, or an analyser's quality gate such as SonarQube's) cannot merge as it stands, so the finding is at least `[P2] MAJOR` however small the real risk. This holds before the gate has run, when the new code plainly breaks a rule the gate enforces. In the body, name the gate and the rule, then rate the real risk on its own ("SonarQube S8707 fails the quality gate; the real risk is low because only the release job passes these paths"). The rule below, to pick the less severe of two labels, does not lower it: the gate, not the reviewer, decides that it blocks. A false alarm from the analyser is still `[P2]`, with the fix being to suppress it the way the project records suppressions, since it blocks until someone does.

`(Defect)` versus `(Quality)` depends on whether the code behaves wrongly, not on what kind of work the fix is. A missing test is `[P4] MINOR (Quality)` on its own; if the untested code is actually broken, report the bug at its own rank and mention the missing test in the fix.

Documentation behaves wrongly when someone acts on it. A false claim that an operator, user or integrator will follow (a recovery step that doesn't recover, a wrong error code to search for, a compatibility promise the format breaks) is a `(Defect)`, ranked by what following it causes, on the same scale as code: `[P3]` usually, `[P2]` when following it leaves them stuck in normal use, and `[P1]` when following it in normal use loses or corrupts data (a recovery step that deletes the only copy). Stale or imprecise wording that changes no one's action is `[P4] MINOR (Quality)`.

When torn between two labels, pick the less severe one (the higher number) and say what would raise it ("[P3] MINOR (Defect), or [P2] MAJOR if this endpoint is public").

Confidence is separate from severity. A finding is **Confirmed** (traced end to end or reproduced) or **Plausible** (credible path, but the deciding fact is out of reach, such as production config, another service or a runtime condition you can't reproduce). State it only when Plausible, together with what would confirm it. If you could check that yourself (read a file, search, run a test), do it before reporting: the finding is then Confirmed or dropped. A Plausible `[P1] CRITICAL` still belongs at the top. `references/verification.md` has the full rules.

The label is meant to be machine-readable. It is always one of exactly these five strings, spelled and cased as shown, and always the first thing on the finding's line, with no list marker, heading or other text before it (this includes the one-line items under **Also noted**):

- `[P1] CRITICAL`
- `[P2] MAJOR`
- `[P3] MINOR (Defect)`
- `[P4] MINOR (Quality)`
- `[P5] NIT`

The `[Pn]` rank is the primary key: automation can sort and gate on `^\[P[1-5]\]` alone, and the name after it must always match the rank (never `[P2] MINOR (Defect)`). Don't use other severity words (high, low, blocker, medium) instead of these labels.

## The comment format

Use this for every finding, in reports and on PRs alike:

```markdown
[P2] MAJOR <one-line claim: the defect, not the topic>
`path/to/file.py:42`

**Issue:** <what is wrong, in 1-3 sentences, pointing at the code.>

**Why it matters:** <how it fails: concrete input or state → wrong outcome, and who is affected. Cite the lines outside the hunk that the scenario depends on (the definition, the caller, the missing guard).>
<If Plausible: "Plausible: confirmed if <a check you could not make from here>.">

**Suggested fix:** <the specific change; a short snippet if clearer than prose.>
```

- **The label is the first thing in the comment**, exactly one of the five labels above (rank and name), followed by the claim on the same line.
- **Issue, then why, then fix**, always in that order, so the author understands the problem before reading the remedy.
- **Suggest a fix whenever you can.** Keep it minimal and in the codebase's style. If several fixes are reasonable, give the one you'd pick and name the trade-off in a sentence. If you can't propose one, replace the fix section with **Next step:** saying what to check or decide, or ask a question.
- **One defect per comment.** If the same bug appears in five places, make one finding that lists the locations (on a PR, comment on the first and list the rest).
- **Pre-existing problems** add `(pre-existing)` after the full label, for example `[P3] MINOR (Defect) (pre-existing) …`, and only appear if the change depends on them or makes them worse.
- **Self-checked findings** posted past the unattended verifier-run budget (`references/verification.md`) add `(self-checked)` after the full label the same way, for example `[P4] MINOR (Quality) (self-checked) …`. Where a host's format keeps the label in a separate field, follow that format and put `(self-checked)` wherever it allows: at the start of the title, or else at the start of the body. Never drop the marker.
- **Questions are fine** when a finding hinges on something you can't see: `[P2] MAJOR Can user_id be null here?` followed by what breaks if it can.

Example:

````markdown
[P2] MAJOR Refund amount can go negative when a partial refund exceeds the remaining balance
`billing/refunds.py:88`

**Issue:** `issue_refund` subtracts `amount` from `order.balance` without checking it against the remaining balance.

**Why it matters:** two partial refunds of 60 on a 100 order both pass validation (`RefundRequest.validate` at `billing/schemas.py:31` only checks `amount > 0`), leaving a balance of -20 and paying out 20 more than was charged.

**Suggested fix:** reject refunds larger than the remaining balance inside the same transaction:

```python
if amount > order.balance:
    raise RefundExceedsBalance(order.id, amount, order.balance)
```
````

## Change-set integrity and publication guard

Before giving an unqualified merge verdict, reconcile the diff file list with the provider's reported changed-file count and account for any missing/truncated, binary, submodule or LFS content. State the coverage: files fully reviewed, skimmed and unavailable. If material cannot be retrieved, set the verdict to **Incomplete review**, list the missing material, and do not claim the PR is safe to merge. This verdict takes precedence over any otherwise-positive merge assessment.

For PR publication, preserve `reviewed_head_sha`, `reviewed_base_sha` and **`reviewed_merge_base_sha`** (the actual comparison commit used to produce the reviewed diff). **Immediately before POST**, run:

```bash
python <skill-dir>/scripts/check_pr_revision.py --repo <owner/repo> --pr <n> \
  --reviewed-head <head-sha> --reviewed-base <base-sha> --reviewed-merge-base <merge-base-sha>
```

The helper requires an unchanged head. If only the base tip advanced, it queries GitHub's compare API for `merge_base_commit.sha` and accepts the review **only if the merge-base remains identical**; it rechecks the PR refs to detect a base move during that query. A changed merge-base, absent response, inaccessible fork commit or timed-out query stops publication. An unrelated base advance with the *same* merge-base leaves the reviewed diff intact, but new base code can still affect integration compatibility. For high-stakes reviews whose conclusions depend on base-branch context, add `--strict-base` to reject **any** base-tip movement. On failure, re-review the affected revision, regenerate line anchors and reverify findings. Use `reviewed_head_sha` as `commit_id`, never the latest SHA. A preflight check cannot eliminate the race after it; enforce revision matching in the host's posting queue when possible and report staleness if the server rejects an anchor.

## Text report template

```markdown
## Review: <short description of the change>

**Verdict:** <Ready to merge | Merge after fixes | Needs rework | Incomplete review>. <One sentence on the most important issue, why it's clean, or which material was unavailable. Use Incomplete review when change-set coverage cannot be established. Say Ready to merge only when every gating check has passed. While one fails, the verdict is not Ready to merge. While one is still running, name it and its state and make the verdict conditional on it ("Ready to merge once SonarQube passes; it is still running"), never a bare Ready to merge.>

**Scope:** <what was reviewed, e.g. "PR #123 (feature/x → main), 14 files, +420/-85">. Languages: <list>. PR snapshots: <reviewed_head_sha>, <reviewed_base_sha>, <reviewed_merge_base_sha>.

**Coverage:** <N fully inspected, N skimmed, N unavailable; any truncated or binary files and known gaps>.

**Verification:** <mode and safe checks run>; <"N findings checked by fresh verifiers; M refuted and dropped." | "N findings checked by fresh verifiers; M refuted and dropped; K self-checked only, past the verifier-run budget." | "Not independently verified: <reason, e.g. no subagents available>.">

### Findings

<Each finding in the comment format above, most severe first, separated by a blank line or `---`.>

### Also noted

[P3] MINOR (Defect) <item held back by the display limit: claim and `file:line` on one line>

[P4] MINOR (Quality) <another held-back item; one per line, most severe first, each starting with its own full label, blank line between them>

<N [P5] NIT findings omitted>

### Not covered
- <Files skimmed or skipped, checks you couldn't run, assumptions made>
```

## Posting comments on a pull request

Post only when requested by the user or enabled in an explicitly authorized review bot. Submit everything as **one review**, so the author gets a single notification and the comments arrive together:

1. Use the **pinned review snapshot**, not an updated HEAD: record head, base tip, and comparison merge-base. A bare PR number can resolve against the wrong repository; pass `--repo` explicitly.
2. Write the review to a JSON file (comment bodies contain backticks and newlines, so don't pass them on the command line):

   ```json
   {
     "commit_id": "<reviewed_head_sha>",
     "event": "COMMENT",
     "body": "<verdict line, scope, and any findings that can't be anchored to a diff line>",
     "comments": [
       {"path": "billing/refunds.py", "line": 88, "side": "RIGHT", "body": "[P2] MAJOR Refund amount can go negative …"},
       {"path": "billing/refunds.py", "start_line": 90, "line": 94, "side": "RIGHT", "body": "[P3] MINOR (Defect) …"}
     ]
   }
   ```

3. **Immediately before POST**, run the revision guard described above using the recorded head, base, and merge-base. Require an unchanged reviewed head and comparison basis (or unchanged base tip in `--strict-base` mode). Abort and re-review if it fails. Do not edit the payload or perform additional file inspection between this check and publishing.
4. Submit it: `gh api repos/<owner>/<repo>/pulls/<n>/reviews --method POST --input review.json`.

- `line` must be on a line in the PR's diff (`RIGHT` for the new version, `LEFT` for deleted lines). A finding about code outside the diff goes in the review `body` in the same tag-first format.
- Use `"event": "COMMENT"` unless the user asks you to approve or request changes.
- When the fix replaces exactly the commented lines, put it in a GitHub suggestion block so the author can apply it with one click:

  ````markdown
  **Suggested fix:**
  ```suggestion
  if amount > order.balance:
      raise RefundExceedsBalance(order.id, amount, order.balance)
  ```
  ````

## When the change is clean

Say so plainly: "No defects found." Then list what you checked, so the reader knows that "clean" reflects coverage and not a skim. Don't invent findings to look thorough.
