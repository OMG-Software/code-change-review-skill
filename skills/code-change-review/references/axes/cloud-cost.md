# Axis: Cloud Cost

Load when the change provisions or scales infrastructure, calls paid cloud or third-party APIs per request, or raises log, metric or data-transfer volume. Use with `review-angles.md`; `languages/infrastructure.md` covers IaC correctness.

- New always-on resources: instances, databases, NAT gateways, load balancers, minimum replica counts, provisioned capacity.
- Per-request paid calls: a paid API (including model APIs) called in a loop, on every request, or retried without a cap.
- Observability volume: debug-level logs, high-cardinality metric labels, traces sampled at 100% on a hot path.
- Data transfer: egress between regions or out to the internet, large objects fetched repeatedly instead of cached.
- Storage that only grows: buckets, tables or log groups without lifecycle or retention rules.
