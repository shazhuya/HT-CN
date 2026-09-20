# D-073 — HT-CN CI uses workflow-level cancellation for superseded runs

status: `active`

## Decision

The main HT-CN CI workflow uses one workflow-level concurrency group per pull request number or
branch ref, with `cancel-in-progress: true`.

A newer commit on the same PR/ref cancels the entire older workflow run, including downstream
formal-release jobs. Job-local concurrency is removed because it can leave an older workflow alive
while a newer run waits for a downstream job/concurrency slot.

## Rationale

During M6.4, PR #53 produced a stale GitHub Actions run whose job record remained
`in_progress` with no steps while a newer PR run waited. The unchanged candidate had to be
validated through PR #54 on a new PR ref. Workflow-level cancellation makes supersession explicit
and prevents normal rapid governance commits from accumulating stale workflows.

## Boundaries

- This does not weaken any CI gate.
- Pull-request and push validation remain separate groups.
- The latest run for a PR/ref must still execute all event-appropriate gates.
- GitHub server-side branch protection remains a separate external-permission issue under D-072.
