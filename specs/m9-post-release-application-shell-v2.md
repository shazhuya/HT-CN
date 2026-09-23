# M9 post-release — Complete Application Shell v2

status: ready_to_merge

## 1. Product goal

Replace the long-page Stable UI with a predictable Windows-oriented research application.

## 2. Required destinations

### 首页
Must show:
- concise product readiness;
- global instrument search / open-research action;
- recent instruments;
- quick links to research, discovery, and system status;
- no full operator tables or audit walls.

### 个股研究
Must show:
- instrument header and analysis controls;
- chart as the largest surface;
- persistent decision narrative;
- candidate identities in a compact selector;
- tabs for 概要 / 形态与价位 / 市场环境 / 审计;
- changing tabs must not recompute harmonic identity.

### 机会发现
Must show:
- Operator Queue as the main purpose of the page;
- filters and candidate table/cards;
- daily review/history as secondary disclosure;
- selecting a symbol must navigate directly to 个股研究 and run/open that instrument.

### 系统状态
Must show:
- supervisor status;
- market-data status;
- harmonic-runtime status;
- evidence status;
- evidence-insufficient must not be rendered as product failure;
- release/diagnostic details may be progressively disclosed.

## 3. Application shell

- fixed/persistent left navigation on desktop;
- compact global top command bar;
- destination title/breadcrumb;
- mobile/tablet navigation collapses without losing functionality;
- hash/history state should allow refresh/back navigation without adding a router dependency.

## 4. Usability

- default screen must not exceed one primary viewport before the user chooses to drill down;
- no duplicated major actions;
- no requirement to understand M3/M4/M5/M9 naming;
- selected instrument must remain visible while switching research tabs;
- recent research list stored locally only as presentation state;
- keyboard Enter from global symbol search opens research.

## 5. Regression

- TypeScript/Vite build;
- destination navigation browser acceptance;
- global search -> research workflow;
- discovery candidate -> research workflow;
- research tab switching does not refetch/recompute analysis;
- existing lifecycle/chart identity and Source boundary tests;
- Phase18/21;
- M4 37/37 and Outcome 4/4.

## 6. Exit

Ready when the application no longer relies on one vertically stacked page for normal operation and the full hosted CI is green without user-PC validation.
