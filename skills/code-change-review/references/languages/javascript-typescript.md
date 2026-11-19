# JavaScript / TypeScript Review Notes

Covers `.js`, `.jsx`, `.mjs`, `.cjs`, `.ts`, `.tsx`, `.vue`, `.svelte`. Use with `review-angles.md`. Check `tsconfig.json` (`strict`, `noUncheckedIndexedAccess`), ESLint/Biome config and `package.json` `engines`/`type` before flagging style or module issues.

## Correctness traps
- `==` versus `===`; `NaN !== NaN`; `typeof null === "object"`.
- Falsy-value bugs: `x || default` replaces `0`, `""` and `false`; use `??`.
- `array.sort()` without a comparator sorts lexicographically (`[10, 9, 1]` becomes `[1, 10, 9]`); `sort` mutates in place.
- `forEach` with an `async` callback: nothing awaits it.
- `for...in` over arrays (string keys, inherited props); use `for...of`.
- Floating-point money; `parseInt` without a radix; `Number("")` is `0`.
- Dates: months are 0-indexed; `new Date("2024-01-01")` is UTC but `new Date("2024/01/01")` is local.
- `this` binding lost when passing methods as callbacks.
- Shallow copies (`{...obj}`, `[...arr]`) mutated deeply; `structuredClone` exists.
- Object used as a map with user keys (`__proto__`, `constructor`); use `Map` or `Object.create(null)`.

## TypeScript specifics
- `as` casts and non-null `!` assertions that hide real nullability. Each one is a claim the reviewer should check.
- `any` leaking into public types; `@ts-ignore` / `@ts-expect-error` added without justification.
- Type guards that lie (`x is Foo` with an incomplete check).
- Exhaustiveness: `switch` on a union without a `never` default misses new members.
- Types only exist at compile time: runtime input (JSON, request bodies, env) needs validation (zod, valibot, etc.), not just a type annotation.
- `enum` versus union-of-literals consistency with the codebase; `const enum` across package boundaries.

## Async and error handling
- Floating promises (no `await`, no `.catch`): unhandled rejections can crash Node.
- `await` in loops where `Promise.all` is intended, or the reverse: `Promise.all` over thousands of items with no concurrency limit.
- `Promise.all` fails fast; is `allSettled` needed?
- `try/catch` around non-awaited promises catches nothing.
- `catch (e)` where `e` is `unknown`: accessing `e.message` without narrowing.
- Event listeners, intervals and subscriptions never removed (leaks).

## Security
- XSS: `innerHTML`, `outerHTML`, `document.write`, `dangerouslySetInnerHTML`, `v-html`, `{@html}` with untrusted data; `href={userUrl}` allowing `javascript:`.
- `eval`, `new Function`, `setTimeout(string)`.
- Prototype pollution: deep merge or `lodash.merge`/`set` with user-controlled keys.
- Node: `child_process.exec` with interpolation (use `execFile`/`spawn` with an args array); `path.join` with user input (traversal); `fs` with user paths.
- SSRF: server-side `fetch(userUrl)`.
- Secrets in client bundles (`NEXT_PUBLIC_*`, `VITE_*` and similar are public by design).
- JWT: `jwt.decode` used where `verify` is needed; `alg: none` acceptance.
- CORS `origin: "*"` with credentials; reflecting the `Origin` header.
- ReDoS in regexes applied to user input.

## Performance
- React: new object, array or function props each render breaking memoization *where it matters*; missing or incorrect `key` (index keys on reorderable lists); expensive work in render; effects that set state and re-trigger themselves.
- Bundle size: importing a whole library (`import _ from "lodash"`, moment) for one function; server-only modules imported in client components.
- Sync fs, crypto or `JSON.parse` of huge payloads on the Node event loop.
- N+1 in resolvers (GraphQL without a dataloader) or ORM loops (Prisma/TypeORM).

## React and framework notes
- Hooks rules: conditional hooks; `useEffect` dependency arrays missing deps (stale closures) or containing unstable ones (infinite loops).
- Effects without cleanup (subscriptions, timers, abort controllers for fetch).
- State updates after unmount; race between overlapping fetches (the last response wins rather than the latest request).
- Next.js: data fetched in client components that should be server-side; `"use client"` boundary leaking server secrets; caching or revalidation behaviour changes.
- Vue: mutating props; reactivity lost by destructuring `reactive()` objects.
- Accessibility: clickable `div`s without role or keyboard handling; images without `alt`; form inputs without labels.

## Modules and packaging
- ESM/CJS mixing (`require` in an ESM package, `__dirname` in ESM).
- `dependencies` versus `devDependencies` placement; the lockfile updated alongside `package.json`.
- Removing exports or changing a function's signature in a published package is breaking.

## Tests (Jest/Vitest/Playwright)
- Missing `await` on async assertions (`expect(promise).rejects` without `await` always passes).
- Fake timers not restored; module mocks leaking across tests.
- Snapshot tests updated wholesale without review.
- E2E selectors tied to CSS classes rather than roles or test IDs.
