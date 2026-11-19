---
name: code-change-review
description: Review a code change (local diff, staged changes, branch, commit range, or pull request) for correctness, security, performance, reliability, compatibility, altitude, duplication, simplicity and test quality, with language-specific checks loaded only for the languages the change touches, and report each finding as a comment tagged [CRITICAL], [MAJOR], [MINOR] or [NIT] with the issue, why it matters and a suggested fix. Use this whenever the user asks to review code or a pull request in any form — "review PR 123", "review PR #45", "review this PR https://github.com/org/repo/pull/123", "look at this PR <url>", "review my branch", "review this diff/commit" — or asks to check changes before merging or committing, "is this safe to ship?", "what did I break?", "look over my changes", or wants a second opinion on a change, even if they don't say the word "review".
---

# Code Change Review

Review a change the way a strong senior engineer would: find the defects that matter, prove each one, and report them so the author can act quickly. A short review with three real bugs beats a long one with thirty maybes, because every false positive teaches the reader to skim.

## Workflow

### 1. Pin down the change set

Work out exactly what is under review before reading any code. If the user didn't say, default to everything not yet on the base branch.

| Target | How to get it |
|---|---|
| Uncommitted work | `git diff HEAD` (plus `git status` for untracked files, then read them) |
| Staged only | `git diff --cached` |
| Current branch | `git diff $(git merge-base HEAD <base>)` where `<base>` is usually `main`/`master` |
| Commit range | `git diff A..B` |
| Pull request (number or URL) | `gh pr view <n-or-url>` for the description, base and head; `gh pr diff <n-or-url>` for the diff; `gh pr diff <n-or-url> --name-only` for the file list |
| Specific files | Read them; ask what they changed from if it matters |

**Pull requests.** "Review PR 123" or "review PR #123" means PR 123 in the current repository. A URL (`https://github.com/<owner>/<repo>/pull/<n>`) can be passed to `gh` as is, and works from any directory, even for another repository. For a GitLab merge request use `glab mr view` / `glab mr diff`. The diff alone is not enough context (step 3), so read the PR's versions of the files too:

- If the PR is from the current repository, fetch it and its base without switching branches, into a dedicated ref that is force-updated so a rebased PR replaces any copy from an earlier review. Fetch from the remote that points at the PR's base repository (check `git remote -v`); in a fork that is usually `upstream`, not `origin`:

  ```bash
  git fetch <remote> <base> +refs/pull/<n>/head:refs/review/pr-<n>
  git rev-parse refs/review/pr-<n>    # must equal: gh pr view <n> --json headRefOid --jq .headRefOid
  ```

  If the fetch fails or the commit doesn't match `headRefOid`, stop and say so rather than review the wrong or a stale copy. Then read files with `git show refs/review/pr-<n>:<path>` and compare against `$(git merge-base refs/review/pr-<n> <remote>/<base>)`. Use `gh pr checkout <n>` only if the user is fine with their working tree changing.
- For another repository, read files at the PR head through `gh api "repos/<owner>/<repo>/contents/<path>?ref=<head-sha>"` (quoted, since `?` is a glob character in zsh), or clone it to a temporary directory if the review needs a lot of context.
- Read the existing feedback so you don't repeat what's been raised, answered or resolved. `gh pr view <n> --comments` shows only top-level comments; inline review threads, their replies and whether each is resolved come from GraphQL:

  ```bash
  gh api graphql -F owner=<owner> -F repo=<repo> -F n=<n> -f query='query($owner:String!,$repo:String!,$n:Int!){repository(owner:$owner,name:$repo){pullRequest(number:$n){reviewThreads(first:100){nodes{isResolved isOutdated path line comments(first:50){nodes{author{login} body}}}}}}}'
  ```

Also get the **intent**: the PR description, commit messages, linked issue, or ask the user in one line if none exists. You can't judge whether code is right without knowing what it is meant to do.

For very large changes (more than ~1,500 changed lines), triage first. Rank files by risk (auth, payments, data migrations, concurrency, public APIs, and anything deleted come before docs, generated code and lockfiles) and say which files got a lighter pass.

### 2. Load language guidance for what the change touches

Load only the reference files for languages and file types in the change set, never all of them. Each file adds context that crowds out the code you're reviewing.

Run the detector if Python is available (`python` or `python3`):

```bash
python <skill-dir>/scripts/detect_languages.py --git <base>   # branch vs base
python <skill-dir>/scripts/detect_languages.py --git HEAD     # uncommitted work
python <skill-dir>/scripts/detect_languages.py --git <remote>/<base> --head refs/review/pr-<n>   # fetched PR
git diff --name-only ... | python <skill-dir>/scripts/detect_languages.py   # any file list
```

For a pull request, use `--head` with the ref fetched in step 1. The detector then reads shebangs from the PR's commit, not from your working tree, which may lack the PR's new scripts or hold different versions of them. For a PR in another repository, `gh pr diff <url> --name-only | python <skill-dir>/scripts/detect_languages.py` gives the file list, but it can't see file contents. Check the first line of each extensionless file it reports as unmapped and route it with the shebang table below.

It prints the reference files to read and which changed files triggered each one. Without Python, use this table, which matches the detector exactly. Filenames match case-insensitively.

| Changed files | Read |
|---|---|
| `.py`, `.pyi`, `.pyw`, `.ipynb`, `pyproject.toml`, `setup.py`, `setup.cfg`, `requirements.txt`, `Pipfile`, `Pipfile.lock`, `poetry.lock`, `uv.lock` | `references/languages/python.md` |
| `.js`, `.jsx`, `.mjs`, `.cjs`, `.ts`, `.tsx`, `.mts`, `.cts`, `.vue`, `.svelte`, `.astro`, `package.json`, `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, `bun.lockb`, `tsconfig.json` | `references/languages/javascript-typescript.md` |
| `.go`, `go.mod`, `go.sum`, `go.work` | `references/languages/go.md` |
| `.rs`, `Cargo.toml`, `Cargo.lock` | `references/languages/rust.md` |
| `.java`, `.kt`, `.kts`, `.scala`, `.sc`, `.groovy`, `.gradle`, `pom.xml`, `build.gradle`, `settings.gradle`, `gradle.properties` | `references/languages/java-kotlin.md` |
| `.cs`, `.fs`, `.fsx`, `.vb`, `.csproj`, `.fsproj`, `.vbproj`, `.sln`, `.razor`, `.cshtml`, `Directory.Build.props`, `Directory.Packages.props`, `NuGet.config`, `global.json` | `references/languages/csharp-dotnet.md` |
| `.c`, `.h`, `.cc`, `.cpp`, `.cxx`, `.c++`, `.hpp`, `.hh`, `.hxx`, `.inl`, `.ipp`, `.m`, `.mm`, `CMakeLists.txt`, `Makefile`, `meson.build`, `conanfile.txt`, `vcpkg.json` | `references/languages/c-cpp.md` |
| `.rb`, `.erb`, `.rake`, `.gemspec`, `.ru`, `Gemfile`, `Gemfile.lock`, `Rakefile`, `config.ru` | `references/languages/ruby.md` |
| `.php`, `.phtml`, `composer.json`, `composer.lock` | `references/languages/php.md` |
| `.swift`, `.pbxproj`, `Package.swift`, `Package.resolved`, `Podfile` | `references/languages/swift.md` |
| `.sql`, `.psql`, `.pgsql`, `.ddl`, and any file under `migration/`, `migrations/`, `migrate/`, `alembic/versions/`, `flyway/`, `liquibase/` | `references/languages/sql.md` |
| `.sh`, `.bash`, `.zsh`, `.ksh`, `.fish`, `.ps1`, `.psm1`, `.psd1`, `.bat`, `.cmd` | `references/languages/shell.md` |
| `.tf`, `.tfvars`, `.hcl`, `.dockerfile`, `Dockerfile`, `Dockerfile*`, `Containerfile`, `.dockerignore`, `compose*.yml`, `compose*.yaml`, `docker-compose*.yml`, `docker-compose*.yaml`, `Chart.yaml`, `values.yaml`, `kustomization.yaml`, `.gitlab-ci.yml`, `azure-pipelines.yml`, `bitbucket-pipelines.yml`, `Jenkinsfile`, any file under `.circleci/`, and YAML under `.github/workflows/`, `.github/actions/`, `k8s/`, `kubernetes/`, `helm/`, `charts/`, `manifests/`, `deploy/`, `deployment/`, `kustomize/`, `argocd/` | `references/languages/infrastructure.md` |

A file with no extension routes by the interpreter on its shebang line (`#!/usr/bin/env deno`, `#!/usr/bin/python3`). Version suffixes are ignored.

| Shebang interpreter | Read |
|---|---|
| `python` | `references/languages/python.md` |
| `node`, `deno`, `bun`, `ts-node`, `tsx` | `references/languages/javascript-typescript.md` |
| `ruby` | `references/languages/ruby.md` |
| `php` | `references/languages/php.md` |
| `sh`, `bash`, `zsh`, `ksh`, `dash`, `fish`, `pwsh` | `references/languages/shell.md` |

One file can need two references. A Rails or Alembic migration needs its language file and `sql.md`, and the detector reports both. A language with no reference file still gets a full review. The general angles below cover it, and you should apply what you know about that language's common pitfalls. Embedded languages count too: SQL strings in Python, or shell commands built in Go, are a reason to load `sql.md` or `shell.md`.

### 3. Build context beyond the diff

The diff shows what changed, not what it affects. Before judging anything:

- **Read the surrounding code** of each hunk, not just the changed lines. Many bugs live in how new lines interact with old ones.
- **Find callers and dependents** of every changed function, type, schema, config key or endpoint (grep, LSP find-references). The blast radius is invisible from the diff.
- **Learn the project's conventions:** linter and formatter configs, `CLAUDE.md`/`CONTRIBUTING.md`, and how nearby code handles errors, logging and tests. Judge consistency against this codebase, not against general taste.
- **Search for existing helpers** before accepting new utility code. Re-implementing something the repo already has only shows up when you look outside the diff.

### 4. Review by angle, in priority order

Work from the top of this list down. A bug in tier 1 matters more than any number of tier 3 notes. `references/review-angles.md` has the full checklist for each angle; read it for any non-trivial review.

1. **Is it right?** Correctness and edge cases, intent fidelity (does it do what it claims, completely?), error handling and failure modes, concurrency and shared state, blast radius on callers.
2. **Is it safe to ship?** Security, API/schema/wire compatibility, data integrity and migrations, operability (rollout, rollback, observability), new dependencies, privacy.
3. **Is it good code?** Performance and efficiency, altitude (is the fix at the right layer?), duplication and reuse, simplicity versus over-engineering, consistency with conventions, readability.
4. **Is it verified?** Tests that would actually fail without the change, documentation and comments kept in sync.

Apply the loaded language file's checks within these angles. They are the specific forms these problems take in that language.

### 5. Verify every finding before reporting it

For each candidate finding:

- **Write the failure scenario:** concrete input or state, then the wrong outcome. If you can't, it's probably not a bug.
- **Re-read the code** to check that the issue isn't already handled: a guard upstream, a validator, a type that rules it out, a test that covers it.
- **Run it** where that's cheap and safe (a unit test, a REPL snippet, the type checker or linter) and the finding is uncertain.
- **Grade confidence:** *Confirmed* (traced or reproduced) or *Plausible* (credible path you couldn't fully prove). Drop anything weaker. If something is unclear but harmless to raise, ask it as a question rather than asserting a bug.

### 6. Report

Use `references/reporting.md` for the severity tags, the comment format and the output template. In short:

- Lead with a one-line verdict: whether it is safe to merge, and the biggest issue if any.
- **Every finding starts with its severity tag: `[CRITICAL]`, `[MAJOR]`, `[MINOR]` or `[NIT]`**, then a one-line claim and its `file:line`. The body explains, in this order, what the issue is, why it is a problem (the concrete failure scenario), and a suggested fix or improvement wherever you can offer one.
- List findings with the most severe first. Default cap of about 10. Mention how many lower-severity items you left out, and list them if the user asks.
- Keep `[NIT]`s out unless there are no real defects, or the user asked for a thorough pass.
- End with what you did *not* cover (files skimmed, things you couldn't run). An honest scope note is part of the review.

Use the same tag-first format for comments posted on a pull request, so a finding reads the same in the report and on the PR. Post to the PR only when the user asks you to; `references/reporting.md` shows how to post them as one review with inline comments.

If the host provides a structured findings tool, report through it in the same order instead of printing the list, and still start each finding's summary with its tag.

## Principles

- **Evidence over opinion.** Every finding cites code. "Consider X" without a reason is noise.
- **Review the change, not the codebase.** Flag pre-existing problems only when the change makes them worse or depends on them, and label them as pre-existing.
- **Respect the author's choices.** A different but equally valid approach is not a finding. Disagree only when you can name a concrete cost.
- **Don't fix during review** unless asked. Suggest fixes; let the user decide whether to apply them.
