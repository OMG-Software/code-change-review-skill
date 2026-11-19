# SQL and Migration Review Notes

Covers `.sql` files, migration files in any framework, and SQL embedded in other languages. Use with `review-angles.md`. Identify the database engine (Postgres, MySQL, SQL Server, SQLite, etc.) first: locking and DDL behaviour differ a lot between engines.

## Query correctness
- `NULL` semantics: `= NULL` is never true (use `IS NULL`); `NOT IN (subquery)` returns nothing if the subquery has a NULL; `COUNT(col)` skips NULLs.
- JOINs: an `INNER JOIN` that should be `LEFT JOIN` (dropped rows); a filter on the right table in `WHERE` turning a LEFT JOIN into an INNER JOIN; join fan-out duplicating rows and inflating `SUM`/`COUNT`.
- `GROUP BY` with non-aggregated columns (MySQL allows it, with arbitrary results).
- `ORDER BY` missing where order matters (pagination, "latest" queries); `LIMIT` without a deterministic order.
- Offset pagination on changing data (skips or duplicates); keyset pagination for large sets.
- Integer division, implicit casts, collation and case-sensitivity differences.
- Time zones: `timestamp` versus `timestamptz`, `NOW()` in the DB versus app time.
- `UPDATE`/`DELETE` without `WHERE`, or with a `WHERE` that matches more than intended.

## Injection
- Any query built by string concatenation or interpolation with input, including `ORDER BY`, column names, `LIMIT` and `IN (...)` lists. Identifiers can't be parameterized, so they need an allowlist.
- Dynamic SQL in stored procedures (`EXEC`/`EXECUTE` with concatenation).

## Concurrency and transactions
- Read-modify-write without `SELECT ... FOR UPDATE`, optimistic version checks or atomic `UPDATE ... SET x = x + 1`.
- Upserts: `INSERT ... ON CONFLICT` / `MERGE` correctness and race-free uniqueness (backed by a unique index).
- Isolation-level assumptions (READ COMMITTED allows non-repeatable reads); long transactions holding locks; transactions spanning network calls.
- Deadlock risk from inconsistent lock ordering across code paths.

## Migrations (high-risk; review carefully)
- **Locking:** on large or hot tables, what lock does the DDL take, and for how long?
  - Postgres: almost every `ALTER TABLE`, including `ADD COLUMN`, takes an `ACCESS EXCLUSIVE` lock. On 11+ a constant default avoids a table *rewrite*, but the lock is still taken. If a long-running transaction holds a conflicting lock, the DDL waits, and every later query queues behind it. Check for a `lock_timeout` (with retry) and for long transactions in that window.
  - Postgres operations that rewrite or scan while locked: volatile defaults, most type changes, `SET NOT NULL`, and adding constraints without `NOT VALID`.
  - MySQL: check `ALGORITHM=INSTANT/INPLACE` support for the specific change, or whether gh-ost/pt-osc is needed.
- Indexes on big tables: `CREATE INDEX CONCURRENTLY` (Postgres; can't run inside a transaction) or online DDL.
- **Mixed-version safety:** old code running against the new schema during deploy. Use expand/contract: add nullable column, then deploy code, then backfill, then enforce. Never rename or drop a column in the same deploy as the code change.
- **Reversibility:** is there a down migration, and does it lose data?
- **Backfills:** batched, idempotent, resumable, not in the same transaction as DDL; throttled to avoid replication lag.
- Constraints: new `NOT NULL`/`UNIQUE`/FK on existing data that may violate it (the migration fails in prod, though it passed on an empty dev DB).
- Data type changes: truncation, precision loss, enum value removal.
- Default values and `NOT NULL` alignment with application model definitions.

## Performance
- Missing indexes for new `WHERE`/`JOIN`/`ORDER BY` patterns; check the composite index column order matches the query.
- Functions on indexed columns in `WHERE` (`LOWER(email) = …`, `DATE(created_at) = …`) defeat indexes.
- Leading-wildcard `LIKE '%x'`; `OR` across different columns; `SELECT *` on wide tables.
- Correlated subqueries per row; N+1 at the app layer.
- Unbounded result sets (no `LIMIT`) on user-facing queries.
- New indexes have write cost; duplicate or redundant indexes.

## Security and data
- Grants or permissions widened; `SECURITY DEFINER` functions with an unsafe `search_path`.
- Row-level security policies bypassed or not added for new tables.
- PII in new columns: encryption, retention, inclusion in logs and exports.
