# Axis: Code That Calls a Language Model

Load when the change sends prompts to a model API or acts on its replies (Anthropic, OpenAI and similar SDKs, agent frameworks, tool-use loops). Use with `review-angles.md`. Instruction files that a model follows are covered by `languages/instructions.md`; this axis is application code.

- Prompt injection: untrusted content (web pages, emails, documents, tool output, user uploads) placed in a prompt for a model that can call tools or take actions. Is that content separated and marked as data, and are the tools it can reach limited to what the task needs, with confirmation for side effects?
- Model output treated as trusted: executed as code or shell, run as SQL, rendered as HTML, used as a file path or URL, or parsed as JSON without validation against a schema. It needs the same handling as any other untrusted input.
- Cost and limits: no maximum on output tokens, input size or tool-call loop iterations; a retry loop on a paid call; a large context sent on every request where caching or trimming applies.
- Model identity: model IDs pinned to a specific version where behaviour must stay stable, and not hard-coded in several places.
- Failure handling: refusals, truncated output (`max_tokens` reached), rate-limit and overload errors, and malformed structured output each have a defined path.
- Tests that assert on exact model wording, or call the live API in unit tests, are flaky and cost money.
