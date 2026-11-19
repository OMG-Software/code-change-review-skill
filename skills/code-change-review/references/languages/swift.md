# Swift Review Notes

Covers `.swift` (plus `Package.swift`, Xcode project changes). Use with `review-angles.md`. Check the Swift language version and strict-concurrency setting (Swift 6 mode changes what the compiler enforces) and SwiftLint config before flagging style.

## Correctness traps
- Force unwraps (`!`), `try!` and `as!` on values that can fail at runtime (network data, user input, file I/O).
- Implicitly unwrapped optionals (`var x: T!`) outside IBOutlets.
- Value versus reference semantics: mutating a struct copy rather than the original; classes shared unintentionally.
- Array index out of range (crashes); `Dictionary` lookups returning optionals ignored with `!`.
- Integer overflow traps at runtime (use `&+` only when wrapping is intended); `Int` to `Int32` conversions crash on overflow.
- `Decodable` models: non-optional fields that the server may omit; date decoding strategy mismatches.
- `switch` with `default` on enums you own (hides new cases); `@unknown default` for system enums.

## Memory
- Retain cycles: closures capturing `self` strongly (stored closures, timers, notification observers, Combine sinks); use `[weak self]` where the closure outlives the call.
- `unowned` where the referent can be deallocated first (crash).
- Delegates declared `strong` instead of `weak`.
- Combine `AnyCancellable` not stored (subscription cancelled immediately), or stored forever.

## Concurrency
- UI updates off the main thread; missing `@MainActor` on UI-touching types or methods.
- Data races on shared mutable state; `Sendable` warnings silenced with `@unchecked Sendable` without justification.
- Actor reentrancy: state assumptions broken across `await` points inside an actor.
- `Task {}` in views or objects not cancelled when they go away; `Task.detached` losing actor context and priority.
- Mixing GCD and async/await (`DispatchQueue.main.async` inside `async` functions); blocking with semaphores on async work (deadlock).
- `nonisolated(unsafe)` and `@preconcurrency` imports hiding real problems.

## Security and privacy
- Secrets in source or `Info.plist`; tokens in `UserDefaults` (use Keychain).
- ATS exceptions (`NSAllowsArbitraryLoads`) added.
- Logging PII with `print`/`NSLog` (use `Logger` with privacy levels).
- URL schemes and universal links: validating parameters before acting.
- WebViews: `WKWebView` JavaScript bridges exposing native functionality to untrusted content.
- New permission usage strings (`NS*UsageDescription`) and privacy manifest updates for new APIs or SDKs.

## SwiftUI / UIKit
- `@State` versus `@StateObject` versus `@ObservedObject` misuse (an `ObservedObject` recreated each render loses state); `@Observable` (iOS 17+) migration consistency.
- Expensive work in `body`; unstable `id`s in `ForEach` causing identity churn.
- UIKit: work in `viewDidLoad` versus `viewWillAppear` repeated; table/collection cell reuse bugs (stale state).
- Accessibility labels, Dynamic Type and dark mode for new UI.

## API and packaging
- Public API changes in packages: `public` to `internal`, changed signatures, `@frozen` types.
- Availability: new APIs used without `#available`/`@available` checks against the deployment target.
- SPM dependency version ranges (`from:` versus `exact:`); `Package.resolved` committed for apps.

## Tests
- Async tests without proper expectations or `await`; timing-based waits.
- UI tests relying on fixed delays rather than element existence.
