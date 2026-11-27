# Axis: Data Integrity and Migrations

Load when the change alters a database schema, writes a migration or backfill, changes ORM models or constraints, or rewrites stored data. Use with `review-angles.md`; `languages/sql.md` has the SQL- and framework-specific forms.

- Reversible? Is there a down migration, or a documented forward-only plan?
- Locking: will `ALTER`/index creation lock a hot table? Is it batched?
- Mixed-version window: the old app running against the new schema, and the reverse.
- Backfills: idempotent, resumable, throttled?
- Constraints: is uniqueness or foreign-key integrity enforced in the DB, or only in app code (which races)?
