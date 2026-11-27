# Axis: Cross-Platform Behaviour

Load when the change builds file paths, runs processes or shell commands, reads or writes text files, or branches on the operating system, in code meant to run on more than one platform. Use with `review-angles.md`; `languages/shell.md` covers shell scripts themselves.

- Path separators and roots: paths joined with `/` or `\` by hand, drive letters, UNC paths, assumptions that absolute paths start with `/`.
- Line endings: `\r\n` versus `\n` in parsing, hashing, comparison and generated files; `.gitattributes` settings for files that must keep one form.
- Case sensitivity: two files differing only in case, or a lookup that works on macOS and Windows but not Linux.
- Shell and process differences: `shell=True`, quoting, commands and flags that exist on one platform only, executable bits, `PATH` lookup.
- Locale and encoding defaults: text read or written without an explicit encoding, number and date parsing that depends on the system locale.
