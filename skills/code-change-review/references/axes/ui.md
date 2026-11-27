# Axis: User Interface

Load when the change renders UI: components, templates, views, styles, or user-facing strings and translation catalogues. Use with `review-angles.md`; XSS is in its Security section.

- Accessibility: labels and accessible names on controls, keyboard operation and focus order, focus moved and restored around dialogs, colour contrast, information not carried by colour alone.
- Internationalization: hard-coded user-facing strings, string concatenation instead of placeholders, pluralization, dates, numbers and currency formatted for the locale, right-to-left layout.
- States: loading, empty, error and partial-data states handled, not only the happy path; double submission prevented while a request is in flight.
- Layout: responsive at the sizes the project supports; long text, large numbers and translated strings that are longer than English.
