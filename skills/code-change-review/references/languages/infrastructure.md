# Infrastructure and Config Review Notes

Covers `Dockerfile`/`Containerfile`, `docker-compose*.yml`, Terraform/OpenTofu (`.tf`, `.tfvars`, `.hcl`), Kubernetes manifests and Helm charts, and CI/CD workflows (GitHub Actions, GitLab CI, Azure Pipelines, etc.). Use with `review-angles.md`. Infra changes often have a bigger blast radius than app code, and mistakes can be hard to roll back.

## Dockerfiles
- Base images: pinned to a specific tag or digest (not `latest`); trusted source; supported and patched version.
- Running as root: add a `USER` with a non-root UID.
- Secrets in `ARG`/`ENV`/`COPY` (they persist in image layers); use BuildKit `--mount=type=secret`.
- `COPY . .` without a `.dockerignore` (ships `.git`, `.env`, `node_modules`, credentials).
- Layer ordering: dependency install before copying source (cache efficiency); `apt-get update` and `install` in the same `RUN`; package caches cleaned.
- Multi-stage builds: build tools left in the final image.
- `HEALTHCHECK`, signal handling (exec-form `CMD`/`ENTRYPOINT` so PID 1 receives SIGTERM).
- `ADD` with remote URLs (no checksum); prefer `COPY` plus a verified download.

## Terraform / OpenTofu
- **Read the plan, not just the code:** does a change force resource replacement (destroy and recreate) on stateful resources (databases, volumes, buckets)? Look for `ForceNew` attributes (name changes, subnet changes, etc.).
- `prevent_destroy` / deletion protection on critical resources; `lifecycle { ignore_changes }` hiding drift.
- Security groups or firewall rules open to `0.0.0.0/0` / `::/0`; public buckets or ACLs; IAM policies with `*` actions or resources.
- Encryption at rest and in transit enabled; logging and audit trails not disabled.
- Secrets in `.tf`/`.tfvars` or outputs (mark `sensitive = true`; use a secret store); state backend encrypted with locking.
- Provider and module versions pinned; `count` versus `for_each` changes re-indexing resources (mass replacement). Use `moved` blocks for refactors.
- Cost: instance sizes, always-on resources, NAT gateways, cross-region traffic.

## Kubernetes / Helm
- Resource `requests`/`limits` set; limits that will OOM-kill or CPU-throttle.
- `securityContext`: `runAsNonRoot`, `readOnlyRootFilesystem`, `allowPrivilegeEscalation: false`, dropped capabilities; no `privileged: true` or `hostNetwork`/`hostPath` without strong reason.
- Probes: liveness probes that kill healthy-but-slow pods; readiness probes present for traffic gating; startup probes for slow boots.
- Rollout safety: `maxUnavailable`/`maxSurge`, `PodDisruptionBudget`, replica counts, graceful shutdown (`terminationGracePeriodSeconds`, `preStop`).
- Secrets in plain ConfigMaps or committed `Secret` manifests (base64 is not encryption).
- RBAC: wildcard verbs or resources; cluster-wide roles where namespace roles fit.
- Image tags mutable (`latest`); `imagePullPolicy` consistency.
- Helm: values defaults changed (affects every release); template logic producing invalid YAML in some value combinations.

## CI/CD workflows
- **GitHub Actions:** third-party actions pinned to a commit SHA (not a mutable tag); `permissions:` minimized (the default token can be broad); `pull_request_target` or `workflow_run` with checkout of PR code (secret exfiltration); untrusted input (`${{ github.event.pull_request.title }}`, branch names, issue bodies) interpolated directly into `run:` scripts (script injection; pass via `env:` instead).
- Secrets echoed to logs, passed to untrusted steps, or available to fork PRs.
- Caching keys that can be poisoned across branches; artifacts containing secrets.
- Deployment jobs: environment protection rules, manual approval for production, concurrency groups to prevent overlapping deploys.
- Tests or linters removed or made non-blocking (`continue-on-error: true`, `|| true`) to get green.
- Self-hosted runners exposed to public-repo PRs.

## General config (YAML/JSON/TOML/.env)
- `.env` or credential files committed; example files containing real values.
- YAML gotchas: unquoted `no`/`yes`/`on`/`off` parsed as booleans (YAML 1.1), leading zeros, `:` in unquoted strings, tab indentation.
- Feature flags or config defaults changed: who else reads this config?
- Environment-specific values (URLs, account IDs) hard-coded in shared config.

## Declarative build files and Terraform JSON
- **Bazel** (`BUILD`, `WORKSPACE`, `MODULE.bazel`, `.bzl`): new external repositories and download rules must be pinned and verified; check visibility changes, hermeticity, caching, remote execution, toolchain selection and reproducible dependency resolution. Generated outputs should not depend on local machine paths or secrets.
- **Nix** (`.nix`, `flake.nix`): check input pins and lockfile changes, impurity (`builtins.getEnv`, network fetches without hashes), architecture-specific branches, secret interpolation and whether changed derivations trigger rebuilds or alter deployments.
- **Terraform JSON** (`*.tf.json`, `*.tfvars.json`): apply the same state, replacement, permission, secret and provider-version checks as HCL; JSON syntax does not reduce rollout risk.
