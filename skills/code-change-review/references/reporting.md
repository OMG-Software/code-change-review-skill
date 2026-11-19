# Reporting Findings

Every finding uses the same shape, whether it appears in a text report, a structured findings tool or a comment on a pull request. Readers learn the shape once and can triage at a glance.

## Severity tags

Rate impact times likelihood, not how interesting the finding is. Each finding starts with exactly one tag.

| Tag | Meaning | Examples |
|---|---|---|
| `[CRITICAL]` | Will cause serious harm in normal use, or is exploitable. Block the merge. | Auth bypass, SQL injection, data loss or corruption, crash on the main path, irreversible migration bug |
| `[MAJOR]` | Wrong behaviour that users or operators will hit, or a serious risk under realistic conditions. Fix before merging. | Race causing duplicate charges, unhandled error on a common path, breaking API change, N+1 on a hot endpoint |
| `[MINOR]` | Wrong in edge cases, a real maintainability or operability cost, or a clear improvement with small impact. Worth fixing, need not block. | Missing timeout, edge-case off-by-one, missing test for new logic, wrong-altitude fix, misleading log message, small duplication |
| `[NIT]` | Style or taste; no behavioural effect. Omit unless there are no real defects, or the user asked for a thorough pass. | Formatting the linter missed, naming, wording |

When torn between two tags, pick the lower one and say what would raise it ("[MINOR], or [MAJOR] if this endpoint is public").

Confidence is separate from severity. A finding is **Confirmed** (traced end to end or reproduced) or **Plausible** (credible path, not fully proven). State it only when Plausible, together with what would confirm it. A Plausible `[CRITICAL]` still belongs at the top.

## The comment format

Use this for every finding, in reports and on PRs alike:

```markdown
[MAJOR] <one-line claim: the defect, not the topic>
`path/to/file.py:42`

**Issue:** <what is wrong, in 1-3 sentences, pointing at the code.>

**Why it matters:** <how it fails: concrete input or state → wrong outcome, and who is affected.>
<If Plausible: "Plausible: confirmed if <check>.">

**Suggested fix:** <the specific change; a short snippet if clearer than prose.>
```

- **The tag is the first thing in the comment**, in capitals and brackets, followed by the claim on the same line.
- **Issue, then why, then fix**, always in that order, so the author understands the problem before reading the remedy.
- **Suggest a fix whenever you can.** Keep it minimal and in the codebase's style. If several fixes are reasonable, give the one you'd pick and name the trade-off in a sentence. If you can't propose one, replace the fix section with **Next step:** saying what to check or decide, or ask a question.
- **One defect per comment.** If the same bug appears in five places, make one finding that lists the locations (on a PR, comment on the first and list the rest).
- **Pre-existing problems** add `(pre-existing)` after the tag, for example `[MINOR] (pre-existing) …`, and only appear if the change depends on them or makes them worse.
- **Questions are fine** when a finding hinges on something you can't see: `[MAJOR] Can user_id be null here?` followed by what breaks if it can.

Example:

````markdown
[MAJOR] Refund amount can go negative when a partial refund exceeds the remaining balance
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
- [MINOR] <lower-severity items held back from the main list, one line each>
- <N [NIT]s omitted>

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
       {"path": "billing/refunds.py", "line": 88, "side": "RIGHT", "body": "[MAJOR] Refund amount can go negative …"},
       {"path": "billing/refunds.py", "start_line": 90, "line": 94, "side": "RIGHT", "body": "[MINOR] …"}
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
