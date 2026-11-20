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
| `[P5] NIT` | Style or taste; no behavioural effect. Omit unless there are no real defects, or the user asked for a thorough pass. | Formatting the linter missed, naming, wording |

`[P1]` and `[P2]` block the merge; `[P3]` to `[P5]` do not.

`(Defect)` versus `(Quality)` depends on whether the code behaves wrongly, not on what kind of work the fix is. A missing test is `[P4] MINOR (Quality)` on its own; if the untested code is actually broken, report the bug at its own rank and mention the missing test in the fix.

When torn between two labels, pick the less severe one (the higher number) and say what would raise it ("[P3] MINOR (Defect), or [P2] MAJOR if this endpoint is public").

Confidence is separate from severity. A finding is **Confirmed** (traced end to end or reproduced) or **Plausible** (credible path, not fully proven). State it only when Plausible, together with what would confirm it. A Plausible `[P1] CRITICAL` still belongs at the top.

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

**Why it matters:** <how it fails: concrete input or state → wrong outcome, and who is affected.>
<If Plausible: "Plausible: confirmed if <check>.">

**Suggested fix:** <the specific change; a short snippet if clearer than prose.>
```

- **The label is the first thing in the comment**, exactly one of the five labels above (rank and name), followed by the claim on the same line.
- **Issue, then why, then fix**, always in that order, so the author understands the problem before reading the remedy.
- **Suggest a fix whenever you can.** Keep it minimal and in the codebase's style. If several fixes are reasonable, give the one you'd pick and name the trade-off in a sentence. If you can't propose one, replace the fix section with **Next step:** saying what to check or decide, or ask a question.
- **One defect per comment.** If the same bug appears in five places, make one finding that lists the locations (on a PR, comment on the first and list the rest).
- **Pre-existing problems** add `(pre-existing)` after the full label, for example `[P3] MINOR (Defect) (pre-existing) …`, and only appear if the change depends on them or makes them worse.
- **Questions are fine** when a finding hinges on something you can't see: `[P2] MAJOR Can user_id be null here?` followed by what breaks if it can.

Example:

````markdown
[P2] MAJOR Refund amount can go negative when a partial refund exceeds the remaining balance
`billing/refunds.py:88`

**Issue:** `issue_refund` subtracts `amount` from `order.balance` without checking it against the remaining balance.

**Why it matters:** two partial refunds of 60 on a 100 order both pass validation, leaving a balance of -20 and paying out 20 more than was charged.

**Suggested fix:** reject refunds larger than the remaining balance inside the same transaction:

```python
if amount > order.balance:
    raise RefundExceedsBalance(order.id, amount, order.balance)
```
````

## Text report template

```markdown
## Review: <short description of the change>

**Verdict:** <Ready to merge | Merge after fixes | Needs rework>. <One sentence on the most important issue, or why it's clean.>

**Scope:** <what was reviewed, e.g. "PR #123 (feature/x → main), 14 files, +420/-85">. Languages: <list>.

### Findings

<Each finding in the comment format above, most severe first, separated by a blank line or `---`.>

### Also noted

[P3] MINOR (Defect) <lower-severity item held back from the main list: claim and `file:line` on one line>

[P4] MINOR (Quality) <another held-back item; one per line, most severe first, each starting with its own full label, blank line between them>

<N [P5] NIT findings omitted>

### Not covered
- <Files skimmed or skipped, checks you couldn't run, assumptions made>
```

## Posting comments on a pull request

Post only when the user asks. Submit everything as **one review**, so the author gets a single notification and the comments arrive together:

1. Get the head commit from the PR's own repository: `gh pr view <pr-url> --json headRefOid --jq .headRefOid`, or `gh pr view <n> --repo <owner>/<repo> …`. A bare number resolves against the current repository, which may be a different one. Use the same `<owner>/<repo>` in step 3.
2. Write the review to a JSON file (comment bodies contain backticks and newlines, so don't pass them on the command line):

   ```json
   {
     "commit_id": "<head sha>",
     "event": "COMMENT",
     "body": "<verdict line, scope, and any findings that can't be anchored to a diff line>",
     "comments": [
       {"path": "billing/refunds.py", "line": 88, "side": "RIGHT", "body": "[P2] MAJOR Refund amount can go negative …"},
       {"path": "billing/refunds.py", "start_line": 90, "line": 94, "side": "RIGHT", "body": "[P3] MINOR (Defect) …"}
     ]
   }
   ```

3. Submit it: `gh api repos/<owner>/<repo>/pulls/<n>/reviews --method POST --input review.json`.

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
