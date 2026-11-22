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
│   └── detect_languages.py       # changed files -> reference files to load
└── ...                            # see tests/ and evals/ at repository root
```

## How language loading works

1. The skill works out the change set (e.g. `git diff $(git merge-base HEAD main)`).
2. `scripts/detect_languages.py --git main` maps the changed files to reference files by extension, filename, path (migrations, `.github/workflows`, `k8s/`) and shebang. Without Python, the same mapping is a table in `SKILL.md`.
3. Only the matching `references/languages/*.md` files are read. Languages with no reference file still get the general review.

## Installing

- **Claude Code (personal):** copy or symlink `skills/code-change-review` to `~/.claude/skills/code-change-review`.
- **Claude Code (project):** copy it to `<repo>/.claude/skills/code-change-review`.
- **Claude.ai:** package it with skill-creator's `package_skill.py` and upload the `.skill` file.

## Adding a language

1. Create `skills/code-change-review/references/languages/<name>.md`, using an existing file as the template. List only language-specific traps and keep generic advice in `review-angles.md`.
2. Add its extensions and filenames to `EXTENSIONS` / `FILENAMES` in `scripts/detect_languages.py`.
3. Add a row to the routing table in `SKILL.md`.
4. Run `python skills/code-change-review/scripts/detect_languages.py --check`. It fails if the script, the reference files and the SKILL.md table disagree.
