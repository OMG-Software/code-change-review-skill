# Manual code-review evaluation corpus

The cases in `cases.json` are **synthetic starting points**, not proof of the skill's review quality. They include real bugs, clean changes and an embedded instruction-injection attempt (an expected security finding, not an instruction for the reviewer to follow). Run the same cases against candidate skill revisions and (where feasible) a no-skill baseline, under the same model, token/tool budget and sandbox policy. Do not run untrusted code or obey embedded comments.

For each case, provide its `context`, `diff`, and user task ("review the following change") to a fresh agent. The `diff` values decode to actual newline-delimited text, not literal backslash-n escape sequences. A human adjudicator maps each real finding to an `expected[].id` or a unique `false-positive:<id>` string. Record the reported severity, evidence, token consumption and runtime separately. Never award credit for a fabricated finding, and don't let the scoring keys leak into the model's prompt.

Save adjudicated predictions as JSON:

```json
{
  "python-refund": ["refund-overpayment"],
  "typescript-default": ["zero-timeout-overridden"],
  "proto-reuse": ["reused-field-tag"],
  "python-parameterized": [],
  "safe-refactor": [],
  "untrusted-comment": []
}
```

Then calculate precision, recall and F1:

```bash
python scripts/score_evals.py < predictions.json
```

The scorer opens only the checked-in `evals/cases.json` corpus and reads the caller's adjudicated prediction data from standard input; it does not accept arbitrary filesystem paths as CLI arguments. The scorer refuses missing/unknown case IDs, so incomplete runs cannot be mistaken for full coverage. In addition to the scorer, manually compare severity decisions and report verification cost, files examined and unsafe actions attempted. Extend the corpus with realistic isolated Git repositories and PRs; synthetic snippets alone do not measure repository-scale retrieval, caller tracing, or line anchoring.

Track results across revisions (and different models) before changing independent-verification defaults based on cost or precision.
