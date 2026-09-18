# M5 Phase 8 — Cross-Process Operator Rebuild Coordination

## Scope

Phase 8 extends the M5 product execution layer from process-local single-flight to
cross-process coordination for the same Operator cache slot.

It does not change Queue semantics, harmonic identity, Source Raw PRZ, Source lifecycle,
M4 enrollment, Outcome Engine semantics, predictive ranking, or trade instructions.

## Why Phase 8 exists

Phase 6 coalesces concurrent rebuilds only inside one Python process.

That is insufficient when:

- the FastAPI process rebuilds the Queue;
- the daily precompute script rebuilds the same Queue;
- multiple API worker processes exist.

Those processes can otherwise run duplicate full-universe scans and race to atomically replace
the same cache file.

## Lock boundary

One filesystem advisory lock protects one cache slot:

- cache root;
- expected trade date;
- bars;
- scales.

The lock intentionally does not split by input identity because different identities still
target the same slot filename and therefore must not write it concurrently.

Different input identities are still not coalesced into one semantic result.

## Lock mechanism

Cross-platform implementation:

- POSIX: `fcntl.flock(LOCK_EX | LOCK_NB)`;
- Windows: `msvcrt.locking(LK_NBLCK)`.

The lock file is only a stable coordination inode.

Lock truth is owned by the operating-system descriptor lock. A process crash closes its
descriptor and releases the lock; a persistent lock file is not treated as a stale-lock owner.

## Request flow

1. try the Phase 7 cache fast path;
2. revalidate current input identity before returning a fast hit;
3. enter process-local single-flight;
4. the local owner acquires the cache-slot filesystem lock;
5. refresh current input identity after any filesystem wait;
6. recheck cache while holding the lock;
7. build only when no valid cache exists for the request's current identity;
8. recheck input identity after full build;
9. cache only a single-as-of, expected-date, input-stable result;
10. release the OS lock in `finally`.

## Force refresh

An uncontended force refresh still rebuilds.

If a force request actually waited behind another process, it may reuse the cache that the prior
owner just produced, but only when that cache validates against the request's still-current
input identity.

This prevents two simultaneous force refreshes from both scanning the full universe.

## Input drift safety

Phase 8 preserves and strengthens Phase 7:

- fast cache hits recheck current identity;
- waiters recheck identity after the cross-process wait;
- post-build identity is rechecked;
- changed input returns live output but does not publish a stale cache.

## Runtime Git hygiene

Product/research runtime trees are ignored:

- `data/product/**`;
- `data/research/**`.

This prevents Queue JSON, lock files and local prospective evidence from making source
`git status` dirty and accidentally blocking clean-worktree research gates.

No runtime data is deleted or rewritten by this Git ignore rule.

## Tests

Coverage includes:

- cache-slot lock path stability;
- contended force refresh cache reuse;
- uncontended force refresh still rebuilding;
- different input identities do not coalesce;
- identity drift during cache hit / lock wait;
- real multiprocessing contention on the actual OS advisory lock;
- runtime Git-ignore contract.

## Frozen research boundary

Audit at final Phase 8 checkpoint:

- M4 capture methodology changed components: 0 / 37;
- Outcome Engine changed components: 0 / 4.

## Acceptance

Validated code checkpoint:

`08f51e28f60840cfb6a85b85fbceb091c9392825`

Hosted CI:

- run `35380339931` / #1641;
- overall: success;
- Python: 658 passed;
- Web build: success;
- Playwright: 21 passed;
- browser evidence upload: success.

## Closeout

Phase 8 is green.

The next M5 stage is the daily close operational pipeline. Old divergent daily-close/handoff
branches may be used as references only; they must not be merged wholesale because their
old dependency graph incorrectly lets M4 strict-QFQ readiness and M4 guards block M5 product
readiness.
