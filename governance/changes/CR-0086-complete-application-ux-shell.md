# CR-0086 — Complete Application UX Shell Refactor

status: closed
baseline_ref: main
baseline_head: 9e228d204082fe19d169e099da16ade11adac658
implementation_baseline_head: 669052a004bf133c6188374b1278d7d0b3d6d07a
target: main
milestone: M9.post_release
work_branch: m9/post-release-ux-shell-v2

## Trigger

The first UI refresh improved visual hierarchy but retained the underlying long single-page interaction model. Direct user feedback after using the refreshed Stable product is that the application is still difficult to use and does not follow normal human application habits.

## Objective

Replace the long-page HT-CN Web UI with a real desktop application information architecture. The product must feel like one coherent research application rather than a collection of engineering cards.

## Application model

Four primary destinations:

1. **首页** — product readiness, global search, recent research, and one obvious next action.
2. **个股研究** — one instrument at a time; chart is primary; decision narrative is persistent; details use tabs.
3. **机会发现** — operator queue, filters, daily changes/history; selecting a candidate opens the research workspace.
4. **系统状态** — runtime/data/harmonic/evidence health, diagnostics and release information.

Within **个股研究**, secondary information is tabbed:
- 概要
- 形态与价位
- 市场环境
- 审计

## UX constraints

- No default long-scroll page containing all product capabilities.
- One dominant task per destination.
- Global symbol search remains available from the application shell.
- Navigation state is explicit and predictable.
- Important user language is Chinese; internal milestone/governance labels are not primary copy.
- Advanced audit data is never deleted, but it is not in the default visual path.
- Candidate selection from opportunity discovery must transition directly into the instrument workspace.
- Runtime faults must remain clearly distinguishable from evidence insufficiency.
- Keyboard and Windows 11 desktop use are first-class.

## Fixed boundaries

No changes to harmonic identity, ratios, Source Raw PRZ, Source lifecycle ownership, M4 methodology, Outcome Engine, evidence authorization, automatic-trading prohibition, 5-0 quarantine, Alternate Bat fail-closed, or HSI unsupported status.

## Validation

See `specs/m9-post-release-application-shell-v2.md`.

## Hosted validation

- Planned candidate `1b33abd1ae31b41e578929d0dd616c95822a5e8b` / run #2735 / workflow 35860762701 passed full hosted product validation after selector-only browser repairs.
- Activated state `6858b4153a26c438b55dce60a08248b664e8cc64` / run #2742 / workflow 35861190465 passed Project OS, Web/application browser flows, Phase18/21, M4 37/37, Outcome 4/4 and Stable acceptance; artifact 10750691642 / sha256:927305bda8e0be5483cd0cd9283fd01cb8675dbb75c463197e258a6aad003c72.
- Exact ready-to-merge head `1d81ac36abf3aabfd219fb40f88414d8ccd98d0c` / run #2751 / workflow 35861724868 passed the full sequence; artifact 10750875542 / sha256:cb1c1ff938882c30add7d9e2d3b4e2aa77cd5c931462ab58bb91b7bed4abea30.

## Closeout

- PR #75 merged with ancestry preserved as canonical main `084a64ddfa7367fcf5c9e17430c618ac6238bf9a`.
- Canonical main workflow 35862565910 / run #2757 passed the full hosted product sequence, including destination-based application browser workflows, Phase18/21, M4 37/37, Outcome 4/4 and Stable acceptance.
- Formal main artifact 10751017238 / sha256:ad002611c8847f0b8c6b8f70104a6cf0c303ff7780939579d82fd36d30fb618d.
- Continuation artifact 10750838328 / sha256:d1897021bdb640a7be8e8e3da88f18ff3b853a19c0ffde7270ea6ff1985ec21b.
- No user-computer execution was required. Core harmonic, Source, M4, Outcome, evidence and automatic-trading boundaries are unchanged.
