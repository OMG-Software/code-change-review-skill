# Axis: Mobile Apps

Load when the change is in an iOS, Android or cross-platform mobile app (Swift, Kotlin, Flutter, React Native), its manifests, entitlements or permissions. Use with `review-angles.md`.

- Lifecycle: work that must finish when the app is backgrounded or killed uses the platform's background mechanisms within their limits; state survives process death and configuration changes.
- Offline and poor networks: requests time out, retry with backoff and queue or fail visibly; no assumption that the server is reachable.
- Battery and data: polling, location, wake locks and large downloads justified and bounded.
- Permissions and privacy: new permissions requested only when needed, with the usage description the store requires; denied permissions handled.
- Compatibility: the minimum OS version the app supports has the APIs the change calls; old app versions in the field still work with any server change.
- App size: large assets or dependencies added to the bundle.
