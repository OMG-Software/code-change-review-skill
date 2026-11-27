# Axis: Dependencies and Copied Code

Load when the change adds, removes or upgrades a dependency (a manifest or lockfile changes), vendors third-party code, or adds a file that carries a licence or copyright header. Use with `review-angles.md`.

- Is the new dependency needed? Is it a large package pulled in for a small function?
- Maintained, reputable, license compatible? Typosquat check on the name.
- Pinned or locked appropriately; the lockfile updated consistently.
- Transitive weight and security advisories.
- Copied or vendored code: a file pasted from another project, a gist or an answer site carries that source's licence. Check its header or origin against the project's licence and how the project is distributed (a copyleft file in a permissively licensed library that others ship). Vendored code also needs its licence text and attribution kept, and a note of where it came from and which version, so that its security fixes can be followed.
