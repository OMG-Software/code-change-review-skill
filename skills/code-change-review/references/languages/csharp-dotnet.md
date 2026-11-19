# C# / .NET Review Notes

Covers `.cs`, `.fs`, `.vb`, `.csproj`, `.razor`, `.cshtml`. Use with `review-angles.md`. Check `<TargetFramework>`, `<Nullable>`, `<LangVersion>`, `.editorconfig` and analyzer settings before flagging style.

## Correctness traps
- Nullable reference types: `!` (null-forgiving) operators hiding real nulls; `#nullable disable` regions; public APIs missing annotations.
- `==` on reference types without an overload compares references; `string.Equals` without `StringComparison` (culture bugs).
- Culture-sensitive parsing and formatting (`double.Parse`, `ToString()`, `ToUpper()`) on machine-readable data; use `CultureInfo.InvariantCulture`.
- Struct copies: mutating a copy from a property or list indexer; mutable structs in general.
- `DateTime` without `Kind` (local versus UTC confusion); prefer `DateTimeOffset` for instants; `DateTime.Now` in server code.
- LINQ deferred execution: enumerating an `IEnumerable` multiple times (re-runs queries); enumeration after the source is disposed.
- `First()` throwing where `FirstOrDefault()` plus a null check is needed (or the reverse: silently defaulting).
- Integer overflow unchecked by default; `decimal` versus `double` for money.
- Pattern matching or `switch` expressions without a discard arm on non-exhaustive types.

## Async
- `async void` (except event handlers): exceptions crash the process and can't be awaited.
- `.Result`, `.Wait()` or `.GetAwaiter().GetResult()` blocking on async code (deadlocks under a sync context, thread-pool starvation).
- Missing `await` (fire-and-forget losing exceptions); `Task` returned but not awaited in `using` scopes (disposed too early).
- `ConfigureAwait(false)` consistency in library code (per codebase convention).
- `CancellationToken` accepted but not passed down, or not accepted on long-running APIs.
- `Task.Run` wrapping async I/O in ASP.NET (wasted threads).
- `ValueTask` awaited twice.

## Resources
- `IDisposable`/`IAsyncDisposable` not disposed (`using`/`await using`).
- `HttpClient` created per request (socket exhaustion); use `IHttpClientFactory` or a shared instance.
- `DbContext` lifetime: shared across threads or held as a singleton (not thread-safe).
- Event handler subscriptions never unsubscribed (memory leaks).

## Concurrency
- `Dictionary<,>` shared across threads; `ConcurrentDictionary.GetOrAdd` factory side effects (may run more than once).
- `lock` on `this`, on types or on strings; `lock` around `await` (not allowed; use `SemaphoreSlim`).
- Static mutable state in web apps (shared across requests).

## Security
- SQL: `FromSqlRaw`/`ExecuteSqlRaw` with interpolation (use `FromSqlInterpolated`, or parameters), `SqlCommand` string concatenation.
- `BinaryFormatter`, `NetDataContractSerializer`, `Newtonsoft.Json` with `TypeNameHandling` other than `None` on untrusted input.
- XML: `XmlDocument`/`XmlTextReader` with DTD processing enabled on old frameworks.
- `Process.Start` with user-built arguments.
- ASP.NET Core: missing `[Authorize]` on new controllers or endpoints, or an `[AllowAnonymous]` added carelessly; over-posting (binding request bodies to entities); anti-forgery disabled; `Html.Raw` with user data; open redirects (`Redirect(returnUrl)` without `LocalRedirect`/`Url.IsLocalUrl`).
- Path traversal with `Path.Combine` (an absolute second argument replaces the first).
- Secrets in `appsettings.json` committed; use user-secrets or a key vault.
- `Random` for tokens; use `RandomNumberGenerator`.

## Performance
- EF Core: N+1 (lazy loading in loops, missing `Include`), client-side evaluation, missing `AsNoTracking` for read-only queries, `ToList()` too early, then filtering in memory.
- Boxing in hot paths; LINQ allocations in tight loops; string concatenation in loops (`StringBuilder`).
- Large object heap allocations (>85KB arrays) in hot paths; consider `ArrayPool`/`Span<T>`.
- Exceptions used for control flow.

## API and build
- Public API changes in libraries (binary versus source compatibility): optional params are baked into callers at compile time; adding interface members breaks implementers (unless default interface methods are used).
- `csproj`: package version ranges, `PrivateAssets`, `TreatWarningsAsErrors` turned off.

## Tests
- `async void` test methods (the framework may not await them).
- Tests sharing static state; `DateTime.Now` not abstracted (`TimeProvider` in .NET 8+).
- Over-mocked EF (in-memory provider behaves differently from real databases).
