# Axis: Privacy and Compliance

Load when the change collects, stores, logs, exports or shares personal data (names, emails, phone numbers, addresses, IP addresses, location, health or payment details), or changes consent, retention or deletion. Use with `review-angles.md`; secrets and PII in logs are in its Security and Operability sections.

- New personal data collected, stored, logged or sent to third parties (analytics, error trackers, model APIs, support tools)? Does the project's privacy notice or data-processing record cover it?
- Retention and deletion paths; data minimization. Does a deletion or export request still reach the new store, cache, index or backup?
- Access: who can read the new data, and is that narrower than the whole service account or team?
