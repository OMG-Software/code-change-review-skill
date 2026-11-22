# code-change-review-skill

A Claude skill for reviewing code changes (diffs, branches, commits, PRs) across correctness, security, performance, reliability, compatibility, altitude, duplication, simplicity and tests. Language-specific guidance is loaded **only for the languages the change touches**.

## Layout

```
skills/code-change-review/
├── SKILL.md                      # workflow, routing table, priorities (always loaded when the skill triggers)
├── references/
│   ├── review-angles.md          # full language-agnostic checklist
│   ├── reporting.md              # severity tags, comment format, report template, posting to a PR
│   ├── verification.md           # proving each finding before reporting it; false-positive patterns
│   └── languages/                # one file per language, loaded on demand
│       ├── python.md
│       ├── javascript-typescript.md
│       ├── go.md
│       ├── rust.md
│       ├── java-kotlin.md
│       ├── csharp-dotnet.md
│       ├── c-cpp.md
│       ├── ruby.md
│       ├── php.md
│       ├── swift.md
│       ├── sql.md                # SQL, embedded queries, and migrations in any framework
│       ├── schemas.md            # Protocol Buffers, GraphQL and Prisma schema changes
│       ├── shell.md              # Bash/sh, PowerShell, Batch
│       ├── infrastructure.md     # Docker, Terraform, Kubernetes/Helm, CI workflows
│       └── instructions.md       # skills, agent prompts, CLAUDE.md: Markdown a model follows
├── scripts/
│   ├── detect_languages.py       # changed files -> reference files to load
│   └── check_pr_revision.py      # fail closed if a reviewed PR head/base has moved
```

## How language loading works

1. The skill works out the change set (e.g. `git diff $(git merge-base HEAD main)`).
2. `scripts/detect_languages.py --git main` maps the changed files to reference files by extension, filename, path (migrations, `.github/workflows`, `k8s/`) and shebang. Without Python, the same mapping is a table in `SKILL.md`.
3. Only the matching `references/languages/*.md` files are read. Languages with no reference file still get the general review.

## Safety and review accuracy

The skill treats PR descriptions, source files, comments, repository instructions and tool output as **untrusted data**, not instructions for the reviewing agent. It defaults to read-only inspection and requires explicit authorization or an approved isolated sandbox to execute project-controlled tests and build tools.

For PR reviews, the agent pins the head SHA, base tip and merge-base used for the actual diff. It verifies change-set completeness and checks that the head and merge-base are unchanged before posting. An unrelated base advance that leaves the merge-base unchanged need not invalidate a review; use `--strict-base` in the publication guard when newer base-branch context also requires re-review.

Review modes: **Quick** (self-check), **Standard** (independent verification for major or uncertain findings), and **Deep** (all reported findings independently verified when subagents are available). Unattended publication uses Deep. The report must disclose coverage and verification limits.

## Validation

```bash
python skills/code-change-review/scripts/detect_languages.py --check
python -m unittest discover -s tests -v
# For manually adjudicated runs (see evals/README.md):
python scripts/score_evals.py < predictions.json
```

GitHub Actions runs the language-routing consistency check and unit tests on pull requests and pushes to `main`; manual evaluation scoring requires adjudicated predictions and is not run in CI. `evals/` contains a small, expandable manual benchmark corpus and a scoring tool; its cases are **not** yet an automatic demonstration of review-model precision or recall.

## Installing

- **Claude Code (personal):** copy or symlink `skills/code-change-review` to `~/.claude/skills/code-change-review`.
- **Claude Code (project):** copy it to `<repo>/.claude/skills/code-change-review`.
- **Claude.ai:** package it with skill-creator's `package_skill.py` and upload the `.skill` file.

## Adding a language

1. Create `skills/code-change-review/references/languages/<name>.md`, using an existing file as the template. List only language-specific traps and keep generic advice in `review-angles.md`.
2. Add its extensions and filenames to `EXTENSIONS` / `FILENAMES` in `scripts/detect_languages.py`.
3. Add a row to the routing table in `SKILL.md`.
4. Run `python skills/code-change-review/scripts/detect_languages.py --check` and `python -m unittest discover -s tests -v`. They fail if the mapping disagrees with the skill table or changes break detector behavior.
