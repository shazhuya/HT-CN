from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from project_state import ROOT, build_resume_pack, validate
from verify_chat_continuation_bundle import verify_bundle

DEFAULT_BUNDLE = ROOT / "artifacts" / "reports" / "htcn-chat-continuation-bundle.zip"
DEFAULT_HANDOFF = ROOT / "logs" / "context" / "HTCN_CHAT_HANDOFF.md"
DEFAULT_PROMPT = ROOT / "logs" / "context" / "HTCN_NEW_CHAT_PROMPT.md"

STATIC_CANONICAL_PATHS = [
    "AGENTS.md",
    "CHAT_CONTINUATION.md",
    "PROJECT_BLUEPRINT.md",
    "README.md",
    ".github/workflows/ci.yml",
    "governance/PROJECT_STATE.json",
    "governance/MILESTONES.json",
    "governance/DECISION_INDEX.json",
    "governance/SOURCE_COVERAGE.json",
    "governance/OPEN_ISSUES.json",
    "governance/QUALITY_BASELINE.json",
    "governance/attempts/2026-09.jsonl",
    "governance/changes/CR-0065-project-os-v2.md",
    "governance/changes/CR-0067-portable-chat-continuity.md",
    "scripts/project_state.py",
    "scripts/context_pack.py",
    "scripts/record_attempt.py",
    "scripts/build_chat_continuation_bundle.py",
    "scripts/verify_chat_continuation_bundle.py",
]


def _git(*args: str, allow_failure: bool = False) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if proc.returncode != 0 and not allow_failure:
        detail = proc.stderr.strip() or proc.stdout.strip() or "git command failed"
        raise RuntimeError(detail)
    return proc.stdout.strip()


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _active_change_path(change_id: str) -> str:
    matches = sorted((ROOT / "governance" / "changes").glob(f"{change_id}-*.md"))
    if len(matches) != 1:
        raise RuntimeError(f"active change must resolve exactly once: {change_id}")
    return matches[0].relative_to(ROOT).as_posix()


def _canonical_paths(state: dict[str, Any]) -> list[str]:
    paths = set(STATIC_CANONICAL_PATHS)
    current = state["current"]
    active_change = current.get("active_change")
    if active_change:
        paths.add(_active_change_path(str(active_change)))
    for rel in state.get("required_specs", []):
        paths.add(str(rel))
    for rel in (state.get("ledgers") or {}).values():
        paths.add(str(rel))

    decisions = json.loads(
        (ROOT / "governance" / "DECISION_INDEX.json").read_text(encoding="utf-8")
    )
    for row in decisions.get("active", []):
        source = row.get("source")
        if source:
            paths.add(str(source))

    ordered = sorted(paths)
    for rel in ordered:
        path = (ROOT / rel).resolve()
        try:
            path.relative_to(ROOT.resolve())
        except ValueError as exc:
            raise RuntimeError(f"canonical path escapes repository: {rel}") from exc
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"canonical file missing or unsafe: {rel}")
    return ordered


def _new_chat_prompt(state: dict[str, Any], head: str) -> str:
    current = state["current"]
    return f"""# HT-CN 新聊天启动提示词

请继续 HT-CN 项目。我已上传 `htcn-chat-continuation-bundle.zip` 或 `HTCN_CHAT_HANDOFF.md`。

不要立即改代码，也不要依赖你对旧聊天的记忆。先完成以下恢复流程：

1. 按 `START_HERE.md` 和 `MANIFEST.json` 检查续接包；
2. 读取仓库权威顺序、PROJECT_STATE、Blueprint、active Change/spec、最新 Attempt、Open Issues、Decision Index 与 Source Coverage；
3. 如可访问 GitHub，核对 canonical main；如不能，明确标注“未在线核对”，不得假装已验证；
4. 先返回一份 **Bootstrap Receipt**，逐项回答协议规定的 11 个问题；
5. 若 bundle、Git、state、ledger 存在任何矛盾，停止核心开发，先报告差异；
6. Receipt 合格后再执行我写在最后的任务；
7. 工作结束前，把成功、失败、用户修改、blocker、Gate 和 next action 写回仓库，不得只留在聊天里；
8. 不需要通读全部旧聊天。仅当本次任务引用了续接包中缺失的具体用户选择时，才定向检索对应旧对话，并把恢复出的重要事实落库。

本续接点应为：

- HEAD: `{head}`
- phase: `{current["phase"]}`
- status: `{current["status"]}`
- active_change: `{current.get("active_change")}`
- active_spec: `{current.get("active_spec")}`

本次要继续的任务：

`<在这里写具体任务；若只写“继续下一步”，AI 必须以 PROJECT_STATE.next_major_task 为准>`
"""


def _start_here(state: dict[str, Any], git_info: dict[str, Any]) -> str:
    current = state["current"]
    private_m1 = state.get("private_m1") or {}
    return f"""# START HERE — HT-CN Portable Continuation Bundle

这是一个只读、白名单、可校验的跨 ChatGPT / 跨 AI 续接包。聊天不是当前状态权威。

## 本包身份

- repository: `{state["repository"]}`
- branch: `{git_info["branch"]}`
- HEAD: `{git_info["head"]}`
- tree: `{git_info["tree"]}`
- canonical branch: `{state["canonical_branch"]}`
- remote main observed locally: `{git_info["remote_main_seen"]}`
- worktree clean: `{str(git_info["worktree_clean"]).lower()}`
- state: `{state["state_id"]}`
- phase/status: `{current["phase"]} / {current["status"]}`
- active change/spec: `{current.get("active_change")} / {current.get("active_spec")}`

## 当前 Gate

- next major task: `{state["next_major_task"]["phase"]} — {state["next_major_task"]["title"]}`
- next human action: `{private_m1.get("one_action_entry") or "(see PROJECT_STATE)"}`
- expected evidence: `{private_m1.get("expected_evidence") or "(see PROJECT_STATE)"}`

## 强制读取顺序

1. `MANIFEST.json`
2. `HTCN_RESUME_PACK.md`
3. `canonical/AGENTS.md`
4. `canonical/governance/PROJECT_STATE.json`
5. `canonical/PROJECT_BLUEPRINT.md`
6. active Change、active spec、Attempt / Issue / Decision / Source ledgers
7. 与本次任务直接相关的 required specs

先输出 Bootstrap Receipt，再工作。协议全文位于 `canonical/CHAT_CONTINUATION.md`。
"""


def _standalone_handoff(
    start_here: str,
    prompt: str,
    resume_pack: str,
    manifest: dict[str, Any],
    canonical: dict[str, bytes],
) -> str:
    parts = [
        "# HT-CN Chat Handoff — Standalone Text Archive\n",
        "> 当目标 AI 无法读取 ZIP 时上传本文件。文件内含同一份 manifest、恢复说明和白名单 canonical 文本。\n",
        start_here,
        prompt,
        resume_pack,
        "# MANIFEST\n\n" + json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        "# CANONICAL FILES\n",
    ]
    for name, payload in canonical.items():
        text = payload.decode("utf-8")
        parts.append(
            f"\n----- BEGIN FILE: {name.removeprefix('canonical/')} -----\n"
            f"{text.rstrip()}\n"
            f"----- END FILE: {name.removeprefix('canonical/')} -----\n"
        )
    return "\n".join(parts).rstrip() + "\n"


def build_bundle(
    bundle: Path = DEFAULT_BUNDLE,
    handoff: Path = DEFAULT_HANDOFF,
    prompt_output: Path = DEFAULT_PROMPT,
    *,
    require_clean: bool = True,
) -> dict[str, Any]:
    ok, errors, warnings, state = validate()
    for warning in warnings:
        print(f"[HT-CN CHAT CONTINUITY] WARN: {warning}")
    if not ok:
        raise RuntimeError(f"Project OS validation failed: {errors}")

    dirty = _git("status", "--porcelain")
    if require_clean and dirty:
        raise RuntimeError(
            "worktree is not clean; commit and record the work unit before generating handoff"
        )

    head = _git("rev-parse", "HEAD")
    git_info = {
        "branch": _git("branch", "--show-current", allow_failure=True) or "(detached)",
        "head": head,
        "tree": _git("rev-parse", "HEAD^{tree}"),
        "origin_url": _git("remote", "get-url", "origin", allow_failure=True) or None,
        "remote_main_seen": _git("rev-parse", "refs/remotes/origin/main", allow_failure=True)
        or None,
        "worktree_clean": not bool(dirty),
    }
    generated_at = datetime.now().astimezone().isoformat(timespec="seconds")
    canonical: dict[str, bytes] = {}
    for rel in _canonical_paths(state):
        canonical[f"canonical/{rel}"] = (ROOT / rel).read_bytes()

    prompt = _new_chat_prompt(state, head)
    start_here = _start_here(state, git_info)
    resume_pack = build_resume_pack(state)
    members: dict[str, bytes] = {
        "START_HERE.md": start_here.encode("utf-8"),
        "HTCN_NEW_CHAT_PROMPT.md": prompt.encode("utf-8"),
        "HTCN_RESUME_PACK.md": resume_pack.encode("utf-8"),
        **canonical,
    }
    entries = [
        {"path": name, "size": len(payload), "sha256": _sha256(payload)}
        for name, payload in members.items()
    ]
    manifest = {
        "schema": 1,
        "kind": "htcn_chat_continuation_bundle",
        "generated_at": generated_at,
        "repository": state["repository"],
        "git": git_info,
        "project": {
            "state_id": state["state_id"],
            "phase": state["current"]["phase"],
            "status": state["current"]["status"],
            "active_change": state["current"].get("active_change"),
            "active_spec": state["current"].get("active_spec"),
            "latest_attempt_id": state["current"].get("latest_attempt_id"),
            "latest_hosted_validation_attempt_id": state["current"].get(
                "latest_hosted_validation_attempt_id"
            ),
            "latest_validation": state["current"].get("latest_validation"),
            "next_major_task": state["next_major_task"],
        },
        "privacy": {
            "whitelist_only": True,
            "raw_private_m1_included": False,
            "runtime_artifacts_included": False,
            "chat_history_included": False,
        },
        "entry_count": len(entries),
        "entries": entries,
    }

    bundle = bundle if bundle.is_absolute() else ROOT / bundle
    handoff = handoff if handoff.is_absolute() else ROOT / handoff
    prompt_output = prompt_output if prompt_output.is_absolute() else ROOT / prompt_output
    bundle.parent.mkdir(parents=True, exist_ok=True)
    handoff.parent.mkdir(parents=True, exist_ok=True)
    prompt_output.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "MANIFEST.json",
            json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"),
        )
        for name, payload in members.items():
            archive.writestr(name, payload)

    standalone = _standalone_handoff(
        start_here,
        prompt,
        resume_pack,
        manifest,
        canonical,
    )
    handoff.write_text(standalone, encoding="utf-8")
    prompt_output.write_text(prompt, encoding="utf-8")
    handoff_hash = _sha256(handoff.read_bytes())
    handoff.with_suffix(".sha256").write_text(f"{handoff_hash}  {handoff.name}\n", encoding="utf-8")

    verify_bundle(bundle, current_root=ROOT)
    print(f"[HT-CN CHAT CONTINUITY] bundle: {bundle}")
    print(f"[HT-CN CHAT CONTINUITY] standalone handoff: {handoff}")
    print(f"[HT-CN CHAT CONTINUITY] new-chat prompt: {prompt_output}")
    print(f"[HT-CN CHAT CONTINUITY] entries: {len(entries)}")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Build HT-CN portable chat continuation bundle")
    parser.add_argument("--output", type=Path, default=DEFAULT_BUNDLE)
    parser.add_argument("--handoff", type=Path, default=DEFAULT_HANDOFF)
    parser.add_argument("--prompt-output", type=Path, default=DEFAULT_PROMPT)
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args()
    try:
        build_bundle(
            args.output,
            args.handoff,
            args.prompt_output,
            require_clean=not args.allow_dirty,
        )
    except (RuntimeError, OSError, zipfile.BadZipFile) as exc:
        print(f"[HT-CN CHAT CONTINUITY] FATAL: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
