# PHP Review Notes

Covers `.php` (plus `composer.json`/`composer.lock`). Use with `review-angles.md`. Check the PHP version (`composer.json` `require.php`), `declare(strict_types=1)` usage and PHPStan/Psalm level before flagging style.

## Correctness traps
- Loose comparison `==` and type juggling (`"abc" == 0` is true before PHP 8; `"1e3" == "1000"`); use `===`.
- `in_array`/`array_search` without `strict: true`; `array_search` returning `0` treated as false.
- `empty()` treats `"0"` as empty; `isset` is false for `null` values.
- Arrays are copied by value, objects by handle; references (`&$x`) in `foreach` left dangling after the loop.
- Integer overflow to float; float money (use integer cents or `bcmath`/brick/money).
- `strpos` returning `0` versus `false`; prefer `str_contains`/`str_starts_with` (PHP 8+).
- Missing return types or nullable types; `mixed` leaking through.
- Date handling: `DateTime` (mutable) versus `DateTimeImmutable`; default timezone assumptions.

## Errors
- `@` error suppression hiding failures.
- Functions returning `false` on error (`file_get_contents`, `json_decode` returns `null`) unchecked; use `JSON_THROW_ON_ERROR`.
- Catching `Exception` but not `Error`/`Throwable` (TypeError, etc.), or catching too broadly.

## Security
- SQL injection: string-built queries in PDO/mysqli; use prepared statements with bound params. Laravel `DB::raw`, `whereRaw`, `orderByRaw` with input; Doctrine DQL concatenation.
- XSS: `echo` of user data without `htmlspecialchars(..., ENT_QUOTES)`; Blade `{!! !!}`; Twig `|raw`.
- `unserialize` on user input (object injection); use `json_decode`.
- `include`/`require` with user-controlled paths (LFI/RFI).
- `exec`, `shell_exec`, `system`, `passthru` and backticks with input (`escapeshellarg` at minimum).
- `extract($_POST)`, variable variables with input.
- File uploads: trusting the client MIME type or extension; storing in web root.
- Weak hashing (`md5`/`sha1` for passwords); use `password_hash`/`password_verify`. `rand`/`mt_rand` for tokens; use `random_bytes`/`random_int`.
- Laravel: mass assignment (`$guarded = []`, `fill($request->all())`); missing authorization (`$this->authorize`, policies, middleware) on new routes; `APP_DEBUG=true` in production.
- Session fixation (no `session_regenerate_id` on login); CSRF tokens missing on forms.

## Performance
- N+1 in Eloquent/Doctrine: relationships in loops without `with()`/eager loading.
- Loading full collections (`->get()`) to count or check existence; use `count()`/`exists()`.
- `chunk` versus `cursor` versus `lazy` for big datasets.

## Tests (PHPUnit/Pest)
- Database tests not wrapped in transactions or refreshed.
- Mocking facades loosely; time not frozen (`Carbon::setTestNow`).
