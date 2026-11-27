# Axis: Cache and Tenant Isolation

Load when the change reads or writes a cache (in-process, Redis, memcached, a CDN or HTTP caching headers), memoizes results, or touches data scoped by tenant or account. Use with `review-angles.md`; cache invalidation and stampedes are in its Concurrency section.

- Every cache key must include each input that changes the result: user, tenant, role or permission set, locale, feature flags, API version. A key built from the path alone serves one user's data to the next. Read the key builder, not the variable name.
- HTTP caching: an authenticated or personalised response must not be cacheable by shared caches (`Cache-Control: private` or `no-store`, `Vary` on the right headers). A CDN rule or `public, max-age` added to a route that reads the session leaks responses across users.
- Multi-tenant data: queries, object storage paths, search indexes, background jobs and logs scoped by tenant on every new path, including jobs that run without a request context.
- Memoization or module-level caches in a server process outlive the request; check they are not keyed only by arguments that are the same for every user.
