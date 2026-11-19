# Go Review Notes

Covers `.go` (plus `go.mod`/`go.sum` changes). Use with `review-angles.md`. Check the `go` directive in `go.mod`: loop-variable semantics changed in Go 1.22, and generics and `slices`/`maps` helpers depend on the version.

## Correctness traps
- **Loop variable capture** in goroutines or closures before Go 1.22 (`for _, v := range xs { go f(&v) }`).
- **Nil interface versus nil pointer:** returning a typed nil pointer as `error` gives a non-nil error.
- Nil map writes panic; nil slice reads are fine. A map read of a missing key returns the zero value silently. Check `v, ok :=`.
- Slice aliasing: `append` may or may not reallocate, so two slices can share a backing array and mutate each other. Sub-slicing large arrays retains memory.
- `range` over a map has random order; don't rely on it in output or tests.
- `defer` in a loop runs at function exit, not iteration end (resource buildup). Deferred args are evaluated immediately.
- Shadowed `err` with `:=` in an inner scope, so the outer `err` is never set.
- Integer overflow on conversions (`int64` to `int32`, `len()` to `uint`).
- `time.Time` compared with `==` (monotonic clock and location); use `.Equal`.
- Struct copies of types containing a `sync.Mutex` (use `go vet` copylocks).

## Errors
- Ignored errors (`_ =` or an unchecked return), especially from `Close()` on writers (data loss), `json.Unmarshal` and `rows.Err()`.
- Wrapping: `fmt.Errorf("...: %w", err)` (not `%v`) when callers use `errors.Is`/`As`; sentinel errors compared with `==` after wrapping.
- `panic` used for ordinary errors in library code; `recover` swallowing everything.
- `log.Fatal` in library code (exits the process, skips defers).

## Concurrency
- Goroutine leaks: blocked sends or receives with no reader or writer, no `ctx.Done()` select, no exit path.
- Data races on maps and shared structs (maps aren't safe for concurrent writes; run `-race`).
- `sync.WaitGroup.Add` called inside the goroutine (race with `Wait`).
- Closing a channel twice, or sending on a closed channel (panic). Only the sender closes.
- Unbuffered channels causing deadlock in single-goroutine paths.
- `context.Context` not propagated: new `context.Background()` inside request paths, ignoring cancellation and deadlines. The `ctx` should be the first param and never stored in structs.
- `time.After` in a loop (leaks timers before Go 1.23); prefer a reused `time.Timer`/`Ticker`.
- `errgroup` without `WithContext` when cancellation on first error is expected.

## Resources and I/O
- `resp.Body.Close()` missing (connection leak); body not drained when connection reuse matters.
- `http.Client{}` with no `Timeout`; `http.DefaultClient` in production paths.
- `sql.Rows` not closed; `rows.Err()` not checked after iteration.
- `ioutil` (deprecated) versus `io`/`os` consistency with the codebase.

## Security
- `exec.Command("sh", "-c", userString)`; prefer an args array.
- SQL built with `fmt.Sprintf`; use placeholders.
- `filepath.Join(base, userInput)` traversal. `filepath.Clean`/`filepath.Rel` checks are lexical only: they don't stop symlink escapes (`base/link -> /etc`). That matters when an attacker can create directory entries, as with archive extraction, uploads or shared directories. In those cases require a traversal-resistant open such as `os.Root`/`os.OpenInRoot`, not a `Rel` check, on Go 1.25.12, 1.26.5, 1.27.0 or later. Earlier releases, including every 1.24 release, follow a final symlink out of the root when the path ends in `/` (GO-2026-4970), so they need an upgrade first. On `GOOS=js`, `os.Root` can't guarantee containment while symlinks change concurrently, so don't treat it as sufficient there.
- `text/template` used for HTML (no escaping); use `html/template`.
- `math/rand` for secrets; use `crypto/rand`.
- `InsecureSkipVerify: true`.
- Unbounded `io.ReadAll` on request bodies (use `http.MaxBytesReader`).

## Performance
- Repeated allocations in hot loops: preallocate slices (`make([]T, 0, n)`), use `strings.Builder`.
- Converting `[]byte` and `string` back and forth in hot paths.
- Reflection or `encoding/json` in tight loops where it matters.
- Mutex contention: holding locks across I/O.

## API and style
- Exported identifiers need doc comments; renaming or removing exported names is a breaking change for importers.
- Accept interfaces, return structs; don't define interfaces on the producer side without need.
- Package naming (no `util`/`common` dumping grounds, no stutter like `user.UserService`).
- `go.mod`: a major version bump requires a `/vN` module path.

## Tests
- Table-driven tests with `t.Run` closures capturing the loop var (pre-1.22) plus `t.Parallel()`.
- `t.Fatal` called from a non-test goroutine (doesn't stop the test).
- Missing `-race` in CI for concurrent code; `time.Sleep`-based synchronization.
