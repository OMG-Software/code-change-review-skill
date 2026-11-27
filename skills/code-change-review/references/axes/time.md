# Axis: Time and Clocks

Load when the change measures durations, sets or checks timeouts, expiries, TTLs or leases, schedules work, or stores or converts timestamps. Use with `review-angles.md`; time-zone, DST and leap-day boundaries are in its Correctness section.

- Durations, timeouts and rate limits measured with the wall clock (`time.time()`, `Date.now()`, `System.currentTimeMillis()`), which jumps when NTP or an operator corrects it. Elapsed time needs a monotonic clock.
- Clock skew between machines: an expiry, lease or token-validity check that compares a timestamp written by one host with the clock of another needs a tolerance, or a single source of time.
- Expiry boundaries: `<` versus `<=` on "expires at", TTLs computed in one unit and compared in another, a token checked as valid and then used after it expired.
- Stored timestamps without a time zone, or converted to local time before storage; schedules ("every day at 02:00") across DST changes.
