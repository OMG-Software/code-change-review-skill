# Python Review Notes

Covers `.py`, `.pyi`, `.ipynb`. Use with `review-angles.md`; this file lists only the Python-specific forms of those issues. Check `pyproject.toml`, `setup.cfg`, `ruff.toml`, `mypy.ini` and similar for the project's Python version and lint rules before flagging style.

## Correctness traps
- **Mutable default arguments** (`def f(x=[])`, `={}`, `=set()`): shared across calls.
- **Late-binding closures** in loops (`lambda: i` captures the variable, not the value).
- `is` versus `==`: `is` on ints or strings works by accident for small values.
- Truthiness: `if x:` is wrong when `0`, `""` or `[]` are valid values. Use `if x is not None:`.
- Integer division (`/` returns float), float equality, `round()` uses banker's rounding.
- Iterating a dict or list while mutating it; `dict.keys()` views reflect later changes.
- Generators consumed twice (second pass is silently empty).
- Naive versus aware `datetime` mixing; `datetime.utcnow()` returns naive (deprecated in 3.12+); `datetime.now()` without tz.
- Shadowing builtins (`list`, `id`, `type`, `input`) or module names.
- `except Exception` hiding bugs; bare `except:` also catches `KeyboardInterrupt`/`SystemExit`.
- Class-level mutable attributes shared across instances.
- `__eq__` defined without `__hash__` (makes the class unhashable), or hashing mutable fields.

## Error handling and resources
- Files, sockets and locks opened without `with`.
- `raise NewError(...)` inside `except` without `from e` loses the cause (or use `from None` deliberately).
- `try/finally` with `return` in `finally` swallows exceptions.
- `assert` for runtime validation: stripped under `python -O`.

## Async and concurrency
- Blocking calls (`requests`, `time.sleep`, sync DB drivers, heavy CPU) inside `async def`: they stall the event loop.
- Coroutine never awaited (created and dropped, so it silently does nothing).
- `asyncio.create_task` result not stored: the task can be garbage-collected mid-flight.
- `asyncio.gather` failure semantics: by default the first exception propagates to the caller, but sibling tasks are **not** cancelled and keep running (and writing) after the caller has handled the error. With `return_exceptions=True`, exceptions come back as results that must be checked. When failure should cancel the rest, prefer `asyncio.TaskGroup` (3.11+).
- Threads and the GIL: CPU-bound work in threads doesn't parallelize; shared state still needs locks (check-then-act is not atomic).
- `multiprocessing` with unpicklable objects or no `if __name__ == "__main__":` guard (breaks on Windows and macOS spawn).

## Security
- `subprocess` with `shell=True` plus interpolated input; `os.system`, `os.popen`.
- `pickle`, `marshal`, `shelve`, `yaml.load` (without `SafeLoader`) on untrusted data. `eval`/`exec` on input.
- SQL built with f-strings or `%`; use parameterized queries (`cursor.execute(sql, params)`).
- `tempfile.mktemp` (race); world-readable files with secrets.
- `requests` with `verify=False`, or without a `timeout` (hangs forever by default).
- Path traversal: `os.path.join(base, user_input)` (an absolute `user_input` discards `base`); check `resolve()` stays under base.
- Jinja2 with `autoescape=False`; Django `mark_safe`, `|safe`, `extra()`, `raw()`; Flask `debug=True` in production.
- `random` for tokens; use `secrets`.
- XML parsing of untrusted input with stdlib parsers (use `defusedxml`).

## Performance
- `list` membership tests in loops (use `set`/`dict`); string `+=` in loops (use `join`).
- ORM N+1: Django missing `select_related`/`prefetch_related`; SQLAlchemy lazy loads in loops.
- Loading whole files or querysets into memory when you could iterate or stream.
- pandas: row-wise `apply`/`iterrows` where a vectorized op exists; chained indexing (`SettingWithCopyWarning`).
- Regex compiled inside hot loops (minor). Catastrophic backtracking on user input (major).

## Typing and API
- Type hints that lie (`Optional` missing, `Any` leaking through public APIs).
- Changing a public function's positional parameter order breaks callers; prefer keyword-only (`*`) for new params.
- Removing or renaming something in `__all__` or a public module is a breaking change.

## Tests (pytest/unittest)
- Fixtures with broad scope (`session`/`module`) mutated by tests, causing order dependence.
- `mock.patch` targeting where a name is *defined* rather than where it is *looked up*.
- Time-dependent tests without freezing time (`freezegun`, `time-machine`).
- `assert` on a tuple (`assert (x, "msg")`) is always true.

## Framework notes
- **Django:** migrations present and reversible for model changes; `null=True` on string fields; missing `on_delete` semantics review; `transaction.atomic` around multi-write operations; `QuerySet.update()` skips `save()` and signals.
- **FastAPI/Pydantic:** response models leaking internal fields; Pydantic v1 versus v2 API mixing; sync endpoints doing heavy work (they run in a threadpool, so that's fine, but async endpoints that block are not).
- **Notebooks (`.ipynb`):** committed outputs containing secrets or PII; cells that only work in execution order.
