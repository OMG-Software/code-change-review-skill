# Reporting Findings

## Severity rubric

Rate impact times likelihood, not how interesting the finding is.

| Severity | Meaning | Examples |
|---|---|---|
| **Critical** | Will cause serious harm in normal use, or is exploitable. Block the merge. | Auth bypass, SQL injection, data loss or corruption, crash on the main path, irreversible migration bug |
| **High** | Wrong behaviour that users or operators will hit, or a serious risk under realistic conditions. | Race causing duplicate charges, unhandled error on a common path, breaking API change, N+1 on a hot endpoint |
| **Medium** | Wrong in edge cases, or a real maintainability or operability cost. | Missing timeout, edge-case off-by-one, missing test for new logic, wrong-altitude fix that will need redoing |
| **Low** | Minor defect or clear improvement with small impact. | Misleading log message, small duplication, unclear name on a public API |
| **Nit** | Style or taste. Omit unless there are no real defects, or the user asked for a thorough pass. | Formatting the linter missed, wording |

Confidence is separate from severity: mark each finding **Confirmed** (traced end to end or reproduced) or **Plausible** (credible path, not fully proven). A Plausible Critical still belongs near the top. Say what would confirm it.

## Output template

Use this structure for a text report:

```markdown
## Review: <short description of the change>

**Verdict:** <Ready to merge | Merge after fixes | Needs rework>. <One sentence on the most important issue, or why it's clean.>

**Scope:** <what was reviewed, e.g. "branch feature/x vs main, 14 files, +420/-85">. Languages: <list>.

### Findings

#### 1. [Critical · Confirmed] <one-line claim>
`path/to/file.py:42`

<What is wrong, in 1-3 sentences.>

**Failure scenario:** <concrete input or state> → <wrong outcome>.

**Suggested fix:** <specific change; a short code snippet if it's clearer than prose>.

#### 2. [High · Plausible] ...

### Also noted
- <Lower-severity items in one line each, if any were held back from the main list>
- <N nits omitted>

### Not covered
- <Files skimmed or skipped, checks you couldn't run, assumptions made>
```

## Writing good findings

- **Claim first.** The title is the defect ("Refund amount can go negative"), not the topic ("Refund logic").
- **One defect per finding.** If the same bug appears in five places, make one finding that lists the locations.
- **The failure scenario is mandatory.** It is how the author checks your claim in seconds rather than minutes.
- **Fixes are suggestions.** Keep them minimal and in the codebase's style. If several fixes are reasonable, name the trade-off in a sentence.
- **Pre-existing issues** get a `(pre-existing)` tag and only appear if the change depends on them or makes them worse.
- **Questions are fine.** "Is `user_id` guaranteed non-null here? If not, line 88 throws" is better than a confident wrong claim.

## When the change is clean

Say so plainly: "No defects found." Then list what you checked, so the reader knows that "clean" reflects coverage and not a skim. Don't invent findings to look thorough.
