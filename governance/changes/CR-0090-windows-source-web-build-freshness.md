# CR-0090 — Windows source-checkout Web build freshness

status: implementing
baseline_ref: main
baseline_head: 04aa35737f7d58c2ab12bca62ba536c3970ce9ef
target: main
milestone: M9.post_release
work_branch: m9/windows-source-build-freshness-v1

## Trigger

A real Windows 11 user updated the Git checkout to the production-recognition mainline, but the running Stable UI still showed the pre-CR-0089 Web bundle: no 1D/60m/15m selector and zero discovery candidates for a Pine-visible ABCD structure. Root cause: source-checkout startup/install accepted any existing apps/web/dist/index.html and never bound the built Web assets to the current Git HEAD.

## Objective

For Git source checkouts only:
- bind built Web assets to the Git HEAD that produced them;
- automatically rebuild when HEAD changes or no build marker exists;
- restart through the existing Stable supervisor without requiring manual deletion of dist;
- leave release-ZIP/no-.git behavior unchanged.

## Frozen boundaries

No recognition, Pine parity, Source identity, M4 methodology, Outcome Engine, lifecycle or trading behavior changes.

## Acceptance

- Windows BAT contract test proves startup detects stale/missing Web build identity.
- Install writes current Git HEAD after successful Web build.
- Release ZIP without .git still trusts packaged built Web and does not require Node.
- Full existing CI/release gates remain green.
