# Ruby / Rails Review Notes

Covers `.rb`, `.erb`, `.rake`, `Gemfile`/`Gemfile.lock`. Use with `review-angles.md`. Check `.ruby-version`, the Rails version and `.rubocop.yml` before flagging style.

## Correctness traps
- Only `nil` and `false` are falsy: `0`, `""` and `[]` are truthy. `blank?`/`present?` versus `nil?` semantics.
- Mutating frozen strings (`# frozen_string_literal: true`); mutating shared constants or default args (`def f(opts = {})` is safe; `DEFAULTS[:x] = …` is not).
- `||=` with legitimately `false`/`nil` values recomputes every time.
- Symbol versus string keys in hashes (`params[:id]` versus `params["id"]`; `HashWithIndifferentAccess` only in Rails params).
- `rescue => e` catches `StandardError` only; `rescue Exception` catches signals and exits too.
- Integer division (`7 / 2 == 3`); `Float` for money (use `BigDecimal`).
- Time zones: `Time.now` versus `Time.current`, `Date.today` versus `Date.current` in Rails.
- Method-missing or metaprogramming hiding typos; `send` with user input calls private methods.

## Rails data layer
- N+1: associations in loops without `includes`/`preload`; counts via `.size` versus `.count` versus `counter_cache`.
- `update_all`, `delete_all`, `update_column` and `insert_all` skip validations and callbacks; intentional?
- Uniqueness validation without a DB unique index (race condition).
- Callbacks with side effects (emails, jobs) firing before the transaction commits; use `after_commit`.
- Migrations: reversible (`change` versus `up`/`down`); adding a column with a default or index on big tables (`algorithm: :concurrently` on Postgres, `disable_ddl_transaction!`); removing columns still referenced (needs `ignored_columns` first).
- `default_scope` surprises; `find_by` returning nil versus `find` raising.
- Loading huge collections with `.all.each` (use `find_each`).

## Security
- SQL injection: string interpolation in `where("... #{x}")`, `order(params[:sort])`, `pluck`/`select` with input, `find_by_sql`.
- Mass assignment: `permit!` or overly broad `permit`.
- XSS: `html_safe`, `raw`, `<%==` with user data; `link_to` with user URLs (`javascript:`).
- `constantize`/`safe_constantize` or `send`/`public_send` on user input.
- `YAML.load` (use `safe_load`), `Marshal.load` on untrusted data.
- Backticks, `system` or `%x` with interpolation; `open(user_input)` (Kernel#open runs `|cmd`).
- Authorization: new controller actions missing `before_action` auth or a Pundit/CanCan check; `skip_before_action` added.
- CSRF: `protect_from_forgery` skipped; `verify_authenticity_token` disabled.
- Open redirect via `redirect_to params[:return_to]`.

## Background jobs and concurrency
- Jobs not idempotent (Sidekiq retries by default); passing whole AR objects rather than IDs.
- Enqueueing inside a transaction (the job runs before commit and can't find the record).
- Thread safety in Puma: class-level mutable state, memoization in class variables.

## Performance
- `each` plus `<<` where `map` fits; repeated string building; `pluck` versus loading full models.
- Caching keys missing versioning (`cache_key_with_version`); Russian-doll invalidation (`touch: true`).

## Tests (RSpec/Minitest)
- `let!` and `before(:all)` leaking state; factories creating large object graphs.
- Time-dependent specs without `travel_to`/`freeze_time`.
- Request specs missing authorization-failure cases.
