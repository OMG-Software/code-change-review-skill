# Axis: Messages, Events and Distributed State

Load when the change publishes or consumes messages or events (queues, streams, pub/sub, webhooks, background jobs), writes to a database and notifies another system, or coordinates work across services. Use with `review-angles.md`.

- Delivery semantics: most queues, streams and webhooks deliver *at least once*. A consumer that charges, emails, increments or inserts on each message must be idempotent: dedupe by a message or idempotency key, or make the write conditional. Settle which semantics apply from the broker client's configuration (acknowledgement mode, auto-commit, redelivery on timeout), not from the queue's name.
- Ordering: are messages for one entity guaranteed to arrive in order (partition key, FIFO group)? A consumer that applies "updated" after "deleted", or an older version over a newer one, needs a version or sequence check.
- Dual writes: writing to the database and publishing an event (or calling another service) as two steps loses one of them when the process dies in between. Look for an outbox, a transaction that covers both, or a reconciliation job.
- Acknowledge after the work, not before; a handler that acks first and then fails loses the message, and one that never acks on a poison message blocks the queue. Is there a dead-letter path and a retry limit?
- Idempotency keys on incoming requests that clients retry (payments, order creation): is the key stored and checked atomically with the effect, and scoped to the caller?
- Sagas and multi-service workflows: is there a compensating step for each forward step, and is it safe to run twice?
