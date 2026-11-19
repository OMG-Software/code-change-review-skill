# Rust Review Notes

Covers `.rs` (plus `Cargo.toml`/`Cargo.lock`). Use with `review-angles.md`. Check the `edition`, `rust-version` (MSRV) and `clippy.toml`/`[lints]` before flagging idioms.

## Correctness and panics
- `unwrap()`/`expect()` on values that can fail in production (input parsing, I/O, lock poisoning, map lookups). Fine in tests and on proven invariants, but the invariant should be evident or commented.
- Indexing (`v[i]`, `&s[a..b]`) panics out of bounds; string slicing panics on non-UTF-8 char boundaries.
- Integer overflow: panics in debug, wraps silently in release. Use `checked_`/`saturating_`/`wrapping_` deliberately. `as` casts truncate or saturate silently.
- `RefCell` double borrow panics at runtime; `Rc` cycles leak.
- Iterator laziness: `map` with side effects never consumed.
- `PartialOrd` on floats (NaN); `sort_by(|a, b| a.partial_cmp(b).unwrap())` panics on NaN.

## Errors
- `?` conversions losing context; consider `anyhow::Context`/`thiserror` sources, consistent with the crate.
- Library crates returning `anyhow::Error` or `Box<dyn Error>` in public APIs where typed errors are expected.
- `let _ = fallible()` discarding a `Result` (the `must_use` warning silenced).
- Error enums: adding variants is breaking unless `#[non_exhaustive]`.

## unsafe
Treat every new or changed `unsafe` block as high-scrutiny.
- Is there a `// SAFETY:` comment, and does it actually justify every invariant (aliasing, alignment, initialization, lifetimes, thread safety)?
- `unsafe impl Send/Sync`: is it truly thread-safe?
- `mem::transmute`, raw pointer arithmetic, `from_raw_parts`, `set_len`, `MaybeUninit` misuse.
- FFI: null checks, ownership across the boundary, panics unwinding across `extern "C"` (UB before the `C-unwind` ABI).
- Could a safe abstraction replace it?

## Concurrency and async
- Holding a `std::sync::Mutex` guard across `.await` (blocks the executor thread, and makes the future `!Send`).
- Blocking calls (std I/O, `thread::sleep`, heavy CPU) in async code without `spawn_blocking`.
- `tokio::spawn` handles dropped: errors and panics lost, no cancellation.
- Cancellation safety: futures in `select!` that lose data when dropped mid-way.
- Lock ordering across multiple mutexes; `RwLock` writer starvation.
- `Arc<Mutex<T>>` where channels or ownership restructuring would be simpler.

## Performance
- Unnecessary `.clone()` / `.to_string()` / `.to_vec()`, especially in loops; borrowing would do.
- `Vec` without `with_capacity` in known-size loops; `collect` then iterate again.
- `Box<dyn Trait>` in hot paths where generics would monomorphize (or the reverse, for code bloat).
- `format!` in hot paths; logging with eager formatting.

## Security
- `std::process::Command` built from input with `sh -c`.
- SQL via `format!` rather than bound parameters (sqlx/diesel).
- Path traversal with `Path::join` (an absolute component replaces the base).
- Deserializing untrusted input into types with no size limits (`serde` and huge `Vec`s).
- Secrets not zeroized where the codebase expects it (`zeroize`, `secrecy`).

## API and semver
- Public API changes: removing items, adding trait methods without defaults, changing generic bounds, adding fields to public structs without `#[non_exhaustive]`. Consider `cargo semver-checks`.
- New dependencies: default features pulled in unnecessarily; `Cargo.lock` committed for binaries.
- Feature flags additive (enabling a feature must not break code).
- MSRV bumps from new std APIs or dependencies.

## Tests
- `#[should_panic]` without `expected =` catches the wrong panic.
- Missing tests for error paths; doc tests out of date.
- Async tests needing `#[tokio::test]` with the right flavor for multi-threaded behaviour.
