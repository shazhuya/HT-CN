# M3 Phase 4 — Action-State Narrative / Product Orchestration

## Objective

Translate the canonical Source lifecycle into a practical observation sequence without creating a trading score or allowing context layers to own state transitions.

The product must answer:

1. 现在在哪；
2. 先看什么；
3. 到了再看什么；
4. 什么条件阻止升级；
5. 当前冻结的下一关键价/角色是什么；
6. 哪些 context 证据当前缺失、过期、冲突或未解析。

## Frozen action-state vocabulary

The UI exposes exactly four broad action states:

- `waiting` — 等待 source gate；
- `reaction_observation` — Source T-Bar 后观察 Type-I reaction；
- `execution_evaluation` — source lifecycle 已形成足够的 execution-stage evidence，可进入执行层评估；
- `evidence_insufficient` — Source PRZ / Source clock 等关键证据不足。

These labels are not buy/sell instructions.

## Ownership

`source_lifecycle.state` is the only owner of action-state classification.

Execution, market, industry, concept and BAMM may:

- add cautions;
- explain tradability;
- explain relative strength;
- expose missing/stale/conflicted evidence.

They may not:

- change `action_state`;
- repair harmonic identity;
- mutate Source Raw PRZ;
- backdate a future observation.

## Product contract

`htcn.app.product_contract` audits assembled analysis payloads.

For every pattern it requires:

- narrative lifecycle state equals canonical source lifecycle state;
- narrative next-key price and role equal lifecycle values;
- action-state can be deterministically rebuilt from lifecycle;
- copied pattern execution context equals top-level execution context;
- every non-current context-integrity layer appears in narrative cautions;
- narrative boundary flags remain false;
- 5-0 remains quarantined.

## Acceptance

`运行M3工作台验收.bat` now requires a real M1 catalog and runs:

1. full Python regression;
2. Web build/type-check;
3. real M1 metadata/tradability read smoke;
4. real M1 product-contract smoke;
5. local API + Workbench;
6. full Playwright acceptance.

Network refresh is deliberately outside deterministic acceptance. Use `运行M3上下文数据同步.bat` separately.
