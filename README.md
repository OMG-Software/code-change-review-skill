# code-change-review-skill

A Claude skill for reviewing code changes (diffs, branches, commits, PRs) across correctness, security, performance, reliability, compatibility, altitude, duplication, simplicity and tests. Language-specific guidance is loaded **only for the languages the change touches**, and checks that matter only for some kinds of code (web requests, caches, messaging, money and so on) are loaded **only when the change contains that kind of code**.

## Layout

```
skills/code-change-review/
├── SKILL.md                      # workflow, routing table, priorities (always loaded when the skill triggers)
├── references/
│   ├── review-angles.md          # core language-agnostic checklist, loaded for every review
│   ├── reporting.md              # severity tags, comment format, report template, posting to a PR
│   ├── verification.md           # proving each finding before reporting it; false-positive patterns
│   ├── axes/                     # one file per review axis (web, caching, messaging, money, ...), loaded on demand
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
│   ├── detect_languages.py       # changed files -> language references and review axes to load
│   ├── review_axes.py            # path rules and content signals that select each axis
│   └── check_pr_revision.py      # fail closed if a reviewed PR head/base has moved
```

## How language and axis loading works

1. The skill works out the change set (e.g. `git diff $(git merge-base HEAD main)`).
2. `scripts/detect_languages.py --git main` maps the changed files to reference files by extension, filename, path (migrations, `.github/workflows`, `k8s/`) and shebang. Without Python, the same mapping is a table in `SKILL.md`.
3. The same run picks review axes from each file's path and contents (imports, API names, keywords), using the rules in `scripts/review_axes.py`. It reads both sides of each change (so a removed signal still counts), at the pinned revision for a PR or from the index with `--staged`, never runs them, and stops at 512 KiB per file.
4. The core checklist (`references/review-angles.md`) is always read; only the matching `references/languages/*.md` and `references/axes/*.md` files are added. Languages with no reference file still get the general review. Because a missed axis drops its checks, the reviewer also reads the axis index in `SKILL.md` after building context and loads any axis the code needs that the detector didn't choose.

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

## Adding a review axis

1. Create `skills/code-change-review/references/axes/<name>.md`: a `Load when` sentence, then the checks. Keep checks that apply to almost every change in `review-angles.md` instead.
2. Add an `Axis` to `scripts/review_axes.py` with the path rules, language references and content signals that select it. Make the signals broad: an extra load costs a little context, a miss drops the axis's checks.
3. Add a row to the axis index in `SKILL.md`.
4. Add the axis to the `axes` field of the eval cases it should route, and run the checks below.

## Adding a language

1. Create `skills/code-change-review/references/languages/<name>.md`, using an existing file as the template. List only language-specific traps and keep generic advice in `review-angles.md`.
2. Add its extensions and filenames to `EXTENSIONS` / `FILENAMES` in `scripts/detect_languages.py`.
3. Add a row to the routing table in `SKILL.md`.
4. Run `python skills/code-change-review/scripts/detect_languages.py --check` and `python -m unittest discover -s tests -v`. They fail if the mapping disagrees with the skill table or changes break detector behavior.
