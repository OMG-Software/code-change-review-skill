# Java / Kotlin / JVM Review Notes

Covers `.java`, `.kt`, `.kts`, `.scala`, `.groovy`, `.gradle` and `pom.xml`. Use with `review-angles.md`. Check the Java target version, Kotlin version and static analysis setup (Error Prone, SpotBugs, detekt, ktlint) before flagging style.

## Correctness traps (Java)
- `==` on `String`, `Integer` or other boxed types (the Integer cache makes `==` work for -128..127 only).
- `equals` overridden without `hashCode` (or the reverse); mutable fields in `hashCode` for objects in hash collections.
- `NullPointerException` from unboxing `null` (`int x = map.get(k)`).
- `Optional.get()` without a check; `Optional` as a field or parameter type (against convention).
- `ConcurrentModificationException`: modifying a collection while iterating (use `Iterator.remove`/`removeIf`).
- `List.of`/`Map.of` are immutable and reject nulls; `Arrays.asList` is fixed-size.
- `BigDecimal` constructed from `double`; `equals` versus `compareTo` (scale matters for `equals`).
- `SimpleDateFormat` (not thread-safe), `java.util.Date`/`Calendar` in new code; prefer `java.time`. `LocalDateTime` where an instant or zone matters.
- Integer overflow in `int` arithmetic (`a * b` before widening), `Math.abs(Integer.MIN_VALUE)`.
- Switch fall-through without `break` (classic switch).

## Kotlin specifics
- `!!` operators: each one is a potential NPE and needs a justification.
- Platform types from Java APIs treated as non-null without checks.
- `lateinit` accessed before initialization; `by lazy` thread-safety mode.
- `data class` with mutable `var` used in sets or maps; `copy()` shallow semantics.
- Coroutines: `GlobalScope` usage; `runBlocking` in production paths; blocking calls on `Dispatchers.Main`/`Default` (use `IO`); swallowed `CancellationException` (rethrow it); structured concurrency broken by launching in the wrong scope.
- `when` without an exhaustive `else` on non-sealed types.

## Errors and resources
- Streams, readers, connections and `ResultSet`s not in try-with-resources (`use {}` in Kotlin).
- Catching `Exception`/`Throwable` broadly; catching `InterruptedException` without restoring the interrupt flag.
- Checked exceptions wrapped and losing the cause (`new RuntimeException(e.getMessage())` rather than `(…, e)`).
- Logging and rethrowing (duplicate logs) versus handling.

## Concurrency
- `HashMap` shared across threads; `ConcurrentHashMap` check-then-put (use `computeIfAbsent`/`merge`).
- Double-checked locking without `volatile`.
- `synchronized` on a non-final field or on `this` for public classes.
- Thread pools: unbounded queues, never shut down, `Executors.newCachedThreadPool` under load; `CompletableFuture` default common pool used for blocking I/O.
- Virtual threads (Java 21+): pinning in `synchronized` blocks around blocking I/O (before Java 24); `ThreadLocal` heavy use.

## Security
- SQL via string concatenation (JDBC `Statement`, JPA JPQL strings, `@Query` with concatenation); use bind parameters.
- Java deserialization (`ObjectInputStream`) of untrusted data; Jackson default typing (`enableDefaultTyping`, `@JsonTypeInfo(use = CLASS)`).
- XXE: `DocumentBuilderFactory`, `SAXParserFactory` and `XMLInputFactory` without disabling external entities.
- `Runtime.exec` with concatenated strings.
- Expression language / SpEL / OGNL evaluated with user input.
- Spring: `@RequestMapping` missing method restriction; actuator endpoints exposed; CSRF disabled without reason; mass assignment binding request bodies straight onto entities.
- Log4Shell-style lookups: user input in log format patterns (check the log4j version).

## Performance
- JPA/Hibernate N+1: lazy collections accessed in loops; missing `JOIN FETCH`/entity graphs; `FetchType.EAGER` on collections.
- String concatenation in loops (use `StringBuilder`); autoboxing in hot loops.
- Streams with heavy per-element allocation in hot paths; `parallelStream` on the common pool for I/O.
- `@Transactional` scope too broad (long transactions holding locks) or ineffective (self-invocation bypasses the proxy; private methods).

## API and build
- Public API changes in libraries: removed methods, changed signatures, new abstract methods on interfaces (use `default`).
- Kotlin: default params need `@JvmOverloads` for Java callers; adding params breaks binary compatibility.
- Gradle/Maven: dependency version conflicts, `implementation` versus `api` exposure, snapshot dependencies in release builds.

## Tests
- Spring context-heavy tests where a unit test would do (slow suites).
- Mockito: over-mocking; `any()` matchers hiding wrong arguments; strict stubs disabled.
- Time and randomness not injected (`Clock`).
