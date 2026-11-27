# Axis: New Public Interfaces

Load when the change adds or reshapes something other code or people call: an exported function, class or type in a library, an HTTP or RPC endpoint, a CLI command or flag, a config key, an event or a file format. Use with `review-angles.md`; compatibility of interfaces that already exist is in its Contracts section.

A new public function, endpoint, CLI flag, config key, event or file format becomes a compatibility promise the day it ships, so judge its shape now, while it is still cheap to change. Report only what has a concrete cost to callers.

- Easy to misuse: boolean or positional parameters whose meaning is invisible at the call site (`send(msg, true, false)`), two parameters of the same type that can be swapped silently, a unit-less number (`timeout: 30`).
- Unsafe defaults: the default should be the safe and common case (validation on, TLS verification on, a bounded page size), with the risky option named as such.
- Hard to extend without breaking: a bare array or scalar returned where a later field will be needed (paginated lists, error details), an enum with no room for an unknown value, an error reported only as a string a caller would have to parse.
- Inconsistent with the interface it sits beside: naming, pagination, error shape, ID format or time format that differs from the project's other endpoints or functions of the same kind.
- One-way doors: identifiers, URLs, wire field names and persisted formats that will be expensive to change once clients or data depend on them. A recorded decision settles these; an accidental choice in an otherwise small change is worth one question.
