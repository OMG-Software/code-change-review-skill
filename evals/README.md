# Manual code-review evaluation corpus

The cases in `cases.json` are **synthetic starting points**, not proof of the skill's review quality. They include real bugs, clean changes and an embedded instruction-injection attempt. The expectation for that case is stored only in evaluation metadata, not in the prompt given to the reviewer. Run the same cases against candidate skill revisions and (where feasible) a no-skill baseline, under the same model, token/tool budget and sandbox policy. Do not run untrusted code or obey embedded comments.

For each case, provide **only** its `context`, `diff`, and user task ("review the following change") to a fresh agent. Keep `id`, `title`, `expected`, and the corpus README out of the model's prompt; they are metadata for evaluation and adjudication. The `diff` values decode to actual newline-delimited text, not literal backslash-n escape sequences. A human adjudicator maps findings to gold-standard IDs. If a model reports a genuine, previously unlisted defect, verify it independently and add a stable ID to the versioned `expected` set **before scoring any model**; score all models against the same frozen adjudicated corpus. Only unsubstantiated or incorrect findings receive unique `false-positive:<id>` labels. The scorer treats unmatched IDs as false positives because it cannot determine correctness from an ID alone. Record the reported severity, evidence, token consumption and runtime separately. Never award credit for a fabricated finding, and don't let the scoring keys leak into the model's prompt.

Save adjudicated predictions as JSON:

```json
{
  "python-refund": ["refund-overpayment"],
  "typescript-default": ["zero-timeout-overridden"],
  "proto-reuse": ["reused-field-tag"],
  "python-parameterized": [],
  "safe-refactor": [],
  "untrusted-comment": ["review-instruction-injection"],
  "docs-journal-code": ["doc-names-stale-code"],
  "docs-recovery-step": ["recovery-misses-archives"],
  "adapter-arguments": ["adapter-outcome-differs"],
  "replay-test": ["replay-uses-open-journal"],
  "docs-limit-accurate": [],
  "rejection-result": ["fallback-over-limit", "size-advice-wrong-tool"],
  "event-size-limit": ["old-build-rejects-escaped-message"],
  "docs-error-layers": []
}
```

Then calculate precision, recall and F1:

```bash
python scripts/score_evals.py < predictions.json
```

The scorer opens only the checked-in `evals/cases.json` corpus and reads the caller's adjudicated prediction data from standard input; it does not accept arbitrary filesystem paths as CLI arguments. The scorer refuses missing/unknown case IDs, so incomplete runs cannot be mistaken for full coverage. When there are missed findings but no predictions, precision is 0 (not 1); when the entire corpus has no findings and no predictions, precision and recall are 1. In addition to the scorer, manually compare severity decisions and report verification cost, files examined and unsafe actions attempted. Extend the corpus with realistic isolated Git repositories and PRs; synthetic snippets alone do not measure repository-scale retrieval, caller tracing, or line anchoring.

Track results across revisions (and different models) before changing independent-verification defaults based on cost or precision.
