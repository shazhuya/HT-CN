# M9 post-release — Stable UI/UX Product Refactor v1

status: ready_to_merge

## 1. User problem

Stable v1.0.0 has the required product capabilities but presents them with engineering-first information architecture. The primary operator journey is buried under runtime, queue, history, evidence and context panels. A usable Stable product must make the daily research workflow obvious without requiring the user to understand internal milestone names.

## 2. Primary journey

The first-screen workflow must support:

1. see concise product/data health;
2. search or select an instrument;
3. run/open analysis;
4. immediately see the interactive chart;
5. see selected harmonic identity and lifecycle;
6. read three human prompts: "现在在哪", "先看什么", "下一步看什么";
7. see the next key price/condition when Source-backed;
8. switch candidate/pattern without losing context;
9. open market/context/audit/evidence/history only when needed.

## 3. Information architecture

Desktop target:
- persistent compact top bar;
- left navigation/observation rail for product sections and candidate discovery;
- main center workspace dominated by chart;
- right decision rail for selected pattern/current state/next observation;
- secondary detail region or drawers for audit/context/history/evidence.

Small-screen target:
- single-column flow preserving the same priority;
- no required horizontal table scrolling for the primary journey;
- secondary dense tables may scroll only inside their own disclosed section.

## 4. Visual system

- coherent dark research-workstation theme;
- Windows 11 / modern desktop feel without imitating any proprietary interface;
- consistent spacing, radii, border hierarchy and typography;
- neutral surfaces with restrained semantic accents;
- A-share red/green only where price direction semantics require it;
- visible keyboard focus and usable disabled/loading states;
- minimum body copy remains readable at normal Windows scaling.

## 5. Usability requirements

- no internal milestone code in the dominant heading;
- primary action wording must describe user intent;
- raw release/git identity is secondary;
- evidence insufficiency is a non-blocking research-state notice, not a scary fault banner;
- empty state must tell the user exactly how to begin;
- errors must state what failed and whether retry is safe;
- primary workflow must not require command-line knowledge.

## 6. Compatibility

Existing API contracts and canonical analysis identity remain unchanged. Preserve browser-test-accessible semantic labels/data-testids where practical; update tests only when the product wording/layout intentionally changes.

## 7. Required regression

- TypeScript build;
- existing browser suite;
- new UI/UX primary-journey test;
- chart pan/zoom identity/no-recompute regression;
- Stable statistical-claims boundary;
- formal M4 37/37 and Outcome 4/4 freeze guards through normal CI.

## 8. Exit criteria

This refactor is ready to merge when:
- the main workspace is chart-first and human-readable;
- operator discovery remains available without dominating the first viewport;
- current-state/next-step narrative is visually first-class;
- secondary engineering detail is progressively disclosed;
- responsive layouts are usable;
- all formal CI gates are green;
- user-computer execution is not required.
