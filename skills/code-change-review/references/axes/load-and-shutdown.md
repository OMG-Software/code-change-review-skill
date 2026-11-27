# Axis: Load, Cancellation and Shutdown

Load when the change runs as a long-lived service or worker, fans work out concurrently, retries or pools calls to other systems, or handles timeouts, cancellation or process signals. Use with `review-angles.md`.

- Unbounded concurrency: fan-out over a list from input (`Promise.all`, a goroutine or task per item, a thread per request) without a semaphore, worker pool or batch size. One large request then exhausts connections, file descriptors or a downstream rate limit.
- Retry amplification: retries at several layers multiply (3 at the client × 3 at the gateway × 3 at the service = 27 calls per failure). Retries without jitter synchronise into waves after an outage.
- Backpressure: a producer that can outrun its consumer needs a bounded queue and a decision for when it is full (block, drop, shed with a clear error), not an in-memory buffer that grows until the process dies.
- Degradation: when an optional dependency (recommendations, analytics, a feature-flag service) is down or slow, does the main path still work, with a short timeout and a fallback, or does it fail or hang with it? A circuit breaker or fallback should exist where the project uses them for similar calls.
- Cancellation: when the caller gives up (request cancelled, deadline passed), is the cancellation passed down to queries and outbound calls, or does work continue for a client that has gone?
- Graceful shutdown: on SIGTERM or a rolling deploy, does the process stop accepting work, finish or hand back in-flight work, and flush buffers within the platform's grace period? New background loops, consumers and timers need to join that shutdown.
- Resource pools: connections or handles taken inside a loop or held across a slow call can exhaust the pool; check the pool size against the new concurrency.
