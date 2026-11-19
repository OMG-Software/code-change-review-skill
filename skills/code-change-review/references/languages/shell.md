# Shell Review Notes (Bash/sh/zsh, PowerShell, Batch)

Covers `.sh`, `.bash`, `.zsh`, `.ps1`, `.psm1`, `.bat`, `.cmd`, scripts with shell shebangs, and shell commands embedded in CI configs or other languages. Use with `review-angles.md`. Check which shell actually runs the script (shebang, CI `shell:` key) and whether ShellCheck/PSScriptAnalyzer is configured.

## Bash / POSIX sh

### Correctness
- **Unquoted variables** (`$var`, `$@`, `$(cmd)`): word splitting and globbing break on spaces and wildcards. Quote everything: `"$var"`, `"$@"`.
- Missing `set -euo pipefail` (or the codebase's equivalent) in scripts where failures should stop execution; `set -e` pitfalls (doesn't trigger inside `if`, `&&` chains or subshell command substitutions in some contexts).
- Bashisms (`[[ ]]`, arrays, `local`, `${var//x/y}`) in scripts with `#!/bin/sh` (dash on Debian/Ubuntu).
- `cd dir` without `|| exit` (later commands run in the wrong directory, which is dangerous with `rm`).
- Parsing `ls` output; `for f in $(find …)` (breaks on spaces; use `find -print0 | xargs -0` or `while IFS= read -r`).
- `read` without `-r` (backslashes mangled).
- `[ $x = y ]` with empty `$x` (syntax error); use quotes or `[[ ]]`.
- Exit codes lost through pipes (without `pipefail`) or by `local var=$(cmd)` (masks the cmd's status).
- GNU versus BSD/macOS tool differences: `sed -i`, `date -d`, `readlink -f`, `grep -P`, `xargs -r`.

### Safety and security
- `rm -rf "$DIR/"*` where `DIR` may be empty or unset, giving `rm -rf /*`. Use `${DIR:?}`.
- `eval` on anything derived from input; unquoted input passed to commands (argument injection: values starting with `-`; use `--`).
- Temp files with predictable names (use `mktemp`); missing `trap` cleanup.
- `curl | bash` installs; downloads without checksum verification; `curl` without `-f` (HTTP errors treated as success).
- Secrets in command-line args (visible in `ps`), echoed to logs, or `set -x` tracing that prints them.
- `sudo` usage added; `chmod 777`.

## PowerShell

### Correctness
- `$ErrorActionPreference = 'Stop'` missing where failures should halt; non-terminating errors silently continue. `try/catch` doesn't catch non-terminating errors without `-ErrorAction Stop`.
- Native command failures don't throw (before PS 7.3's `$PSNativeCommandUseErrorActionPreference`); check `$LASTEXITCODE`.
- `$null` comparisons: put `$null` on the left (`$null -eq $x`), because with arrays on the left `-eq` filters.
- Pipeline unrolling: a single-item result isn't an array (`@()` to force it); functions returning unintended output (uncaptured expressions pollute return values; use `[void]` or `| Out-Null`).
- Windows PowerShell 5.1 versus PowerShell 7 differences (`&&`/`||`, ternary, `ConvertFrom-Json -AsHashtable`, default encodings: 5.1 `Set-Content`/`Out-File` encoding differs).
- `-Force` on `New-Item` for files truncates existing content.
- Paths: `Join-Path` versus string concatenation; `-LiteralPath` for paths with `[ ]`.

### Security
- `Invoke-Expression` with any external input; `Start-Process` with concatenated arguments.
- `-ExecutionPolicy Bypass` added; downloading and executing scripts (`iwr | iex`).
- Credentials as plaintext strings rather than `PSCredential`/`SecureString`/SecretManagement; secrets written to transcripts.

## Batch (.bat/.cmd)
- `%VAR%` expansion inside blocks needs `setlocal EnableDelayedExpansion` and `!VAR!`.
- `errorlevel` checks (`if errorlevel 1` means ≥1); missing `exit /b` codes.
- Unquoted paths with spaces; `call` needed to invoke other batch files and return.

## Portability and operations
- Line endings: CRLF in `.sh` files breaks execution (`$'\r': command not found`); check `.gitattributes`.
- Executable bit set for new scripts (`git update-index --chmod=+x`).
- Idempotency: can the script be rerun safely after partial failure?
- Hard-coded absolute paths, usernames or machine-specific assumptions.
