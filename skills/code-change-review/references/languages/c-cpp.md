# C / C++ / Objective-C Review Notes

Covers `.c`, `.h`, `.cc`, `.cpp`, `.cxx`, `.hpp`, `.hh`, `.m`, `.mm` (plus `CMakeLists.txt`/Makefiles). Use with `review-angles.md`. Check the language standard (`-std=`), compiler warnings, sanitizer usage and the codebase's ownership conventions (raw pointers versus smart pointers) before flagging style.

## Memory safety (highest priority)
- Buffer overflows: `strcpy`, `strcat`, `sprintf`, `gets`, `memcpy` with sizes derived from input; off-by-one on NUL terminators; `strncpy` not NUL-terminating.
- Use-after-free and dangling references: returning pointers or references to locals; iterators, references or `string_view`/`span` into containers that reallocate (`push_back`, `insert`, `erase`); lambdas capturing by reference outliving the scope.
- Double free, mismatched `new[]`/`delete`, `malloc`/`delete`.
- Uninitialized variables and struct fields (especially in new constructors or paths).
- Integer overflow feeding allocation sizes (`malloc(n * size)`); signed/unsigned comparisons; signed overflow is UB.
- Format string bugs: `printf(user_input)`.
- `memset` or `memcpy` on non-trivially-copyable C++ types.

## Undefined behaviour
- Null dereference; strict aliasing violations (type-punning through pointer casts); unaligned access.
- Shifts by negative amounts or by at least the type width; sequence-point violations (`i = i++`).
- Data races (UB in the C++ memory model).
- Calling a pure virtual function (directly or through a helper) from a constructor or destructor; deleting through a base pointer without a virtual destructor.
- Not UB but often a bug: a non-pure virtual call in a constructor or destructor runs the class under construction's version, not the derived override. Flag it only when the code expects the derived one.

## C++ resource management
- Raw `new`/`delete` in new code where `std::unique_ptr`/`make_unique` fits; ownership unclear at API boundaries.
- Rule of 0/3/5: a custom destructor without matching copy and move semantics (double-free on copy).
- `shared_ptr` cycles; `shared_ptr` passed by value in hot paths.
- Exception safety: resources leaked when a later line throws (RAII); destructors that throw.
- `std::move` then use-after-move; `std::move` on `const` (silently copies); returning `std::move(local)` (inhibits RVO).
- Implicit conversions: single-argument constructors not marked `explicit`.

## C error handling
- Return codes unchecked (`malloc`, `fopen`, `read`/`write` partial counts, `pthread_*`).
- `errno` read after an intervening call that may clobber it.
- Cleanup paths: `goto cleanup` patterns missing a resource; early returns leaking.

## Concurrency
- Shared state without a mutex or atomics; `volatile` used as if it gave thread safety (it doesn't).
- Lock ordering; `std::lock_guard` scope too wide (holding across I/O) or too narrow.
- Condition variables waited without a predicate (spurious wakeups).
- `std::thread` destroyed while joinable (`std::terminate`); prefer `std::jthread` (C++20).
- Static initialization order across translation units; thread-safe statics.

## Security
- `system()`/`popen()` with input; `exec*` argument construction.
- TOCTOU on files (`access()` then `open()`).
- Path handling: traversal, symlinks.
- Secrets in memory not cleared (`explicit_bzero`/`SecureZeroMemory`; plain `memset` may be optimized out).
- `rand()` for security purposes.

## Objective-C specifics
- Retain cycles in blocks capturing `self` (use a `weak`/`strong` dance).
- Messaging `nil` returns zero silently, which can hide bugs.
- `NSString` format specifiers mismatched with argument types.

## Performance
- Pass large objects by `const&`; unnecessary copies in range-for (`for (auto x : vec)` instead of `const auto&`).
- `std::endl` flushing in loops; `std::map` where `unordered_map` or a sorted vector fits; reallocations without `reserve`.
- Virtual dispatch or heap allocation in hot inner loops.
- Headers: heavy includes in widely included headers (build time); missing include guards or `#pragma once`.

## API and ABI
- Changing struct layout, class members, virtual function order or inline functions in a shared library breaks ABI.
- Macros: unparenthesized arguments, multiple evaluation of arguments, missing `do { } while (0)`.

## Tests and tooling
- Is new code covered by tests built with ASan/UBSan/TSan in CI, if the project uses them?
- Compiler warnings suppressed (`#pragma warning(disable…)`, `-Wno-…`) to land the change.
