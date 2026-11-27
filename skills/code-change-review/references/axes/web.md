# Axis: Web Requests

Load when the change handles HTTP requests or responses: routes, controllers, handlers, middleware, cookies, CORS or CSRF settings, in any framework. Use with `review-angles.md`. The language files list the framework-specific forms; these apply even where no language file names them.

- CSRF: a state-changing endpoint that authenticates by cookie needs a CSRF token or an `Origin`/`Referer` check. A `SameSite` session cookie narrows the exposure but is not enough alone: `Lax` still sends the cookie on a cross-site top-level `GET`, so a state-changing `GET` stays exposed, and under either `Lax` or `Strict` a page on a sibling subdomain counts as same-site and gets the cookie. Endpoints that take only a bearer token from a header are not exposed.
- CORS: a reflected `Origin` or a wildcard combined with credentials; an allow-list matched by substring or suffix (`evil-example.com` passing a check for `example.com`).
- Cookies: session cookies set without `Secure`, `HttpOnly` and a `SameSite` value; session ID not rotated on login or privilege change (fixation).
- Mass assignment: a request body bound straight onto a model so that a client can set `role`, `owner_id` or `price`.
- Security headers the project sets elsewhere (CSP, `X-Content-Type-Options`, frame protection) missing from a new route or a new server.
- Rate limiting on login, password reset, OTP and other guessable endpoints.
