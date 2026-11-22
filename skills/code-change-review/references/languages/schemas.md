# Schema and Contract Review Notes

Covers Protocol Buffers (`.proto`), GraphQL (`.graphql`, `.gql`, `.graphqls`) and Prisma (`.prisma`). Pair with `review-angles.md` and the relevant server/client language guidance. Schema changes may break clients that are not part of the diff.

## Protocol Buffers and gRPC
- Never reuse a deleted field number or name; reserve removed tags and names. Check compatibility against the published schema, not only the current implementation.
- Verify wire compatibility for type changes, `oneof` moves, scalar/message presence, maps, packed repeated fields and unknown enum values. Proto3 defaults can conflate unset and zero; check required presence semantics.
- New enum definitions should have an appropriate zero value; callers must tolerate unknown values and mixed-version deployments.
- Renaming a field may preserve the wire number but break JSON names, generated APIs and reflection users.
- Check gRPC service/method contracts, streaming lifetime, deadlines, auth, error codes and client retries.
- Regenerate clients/descriptors consistently and run cross-version consumer tests when available.

## GraphQL
- Added non-null fields and arguments may be breaking, including when old stored objects lack a value. Removing/renaming fields, changing argument defaults, tightening nullability or changing enum values can break existing queries.
- Verify resolvers, authorization per field/object, query cost/depth bounds and N+1 behavior.
- Check schema federation, persisted queries, generated client types, pagination/cursors and whether deprecated fields still have consumers.

## Prisma and ORM schemas
- Inspect the *generated SQL migration* as well as schema syntax. Validate indexes, unique constraints, foreign keys, referential actions and nullable-to-required backfills on existing rows.
- Check expand/contract deployment sequencing, application/client versions, data migration batching, rollback plans and concurrent index creation where relevant.
- Verify generated Prisma Client types and downstream callers, including renamed models or relation fields. Schema changes alone may not implement the data migration required.

## Verification
- Compare published contracts to both old and new readers/writers; test mixed versions and clients outside this repository when feasible.
- A schema without changed application code can still be a high-risk change. If consumers or data state are inaccessible, record the specific unverified compatibility assumption instead of claiming safety.
