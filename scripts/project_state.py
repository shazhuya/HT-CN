from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / "governance" / "PROJECT_STATE.json"
BLUEPRINT_PATH = ROOT / "PROJECT_BLUEPRINT.md"
MILESTONES_PATH = ROOT / "governance" / "MILESTONES.json"
DECISIONS_PATH = ROOT / "governance" / "DECISION_INDEX.json"
SOURCE_PATH = ROOT / "governance" / "SOURCE_COVERAGE.json"
ISSUES_PATH = ROOT / "governance" / "OPEN_ISSUES.json"
DEFAULT_RESUME = ROOT / "logs" / "context" / "HTCN_RESUME_PACK.md"

ALLOWED_SOURCE_STATUS = {
    "supported",
    "supported_frozen",
    "quarantined",
    "fail_closed",
    "supported_source_state_machine",
    "supported_source_clock",
    "unsupported",
}

ALLOWED_CHANGE_STATUS = {
    "planned",
    "implementing",
    "validation_failed",
    "validation_green",
    "ready_to_merge",
    "merged",
    "postmerge_pending",
    "closed",
    "blocked",
}


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise RuntimeError(f"missing required JSON: {path.relative_to(ROOT)}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"invalid JSON {path.relative_to(ROOT)}: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"JSON root must be object: {path.relative_to(ROOT)}")
    return payload


def run_git(*args: str, allow_failure: bool = False) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0 and not allow_failure:
        detail = proc.stderr.strip() or proc.stdout.strip() or f"git {' '.join(args)} failed"
        raise RuntimeError(detail)
    return proc.stdout.strip()


def git_commit_exists(sha: str) -> bool:
    proc = subprocess.run(
        ["git", "cat-file", "-e", f"{sha}^{{commit}}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0


def git_is_ancestor(base: str, head: str) -> bool:
    proc = subprocess.run(
        ["git", "merge-base", "--is-ancestor", base, head],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0


def _find_change_file(change_id: str) -> Path:
    matches = sorted((ROOT / "governance" / "changes").glob(f"{change_id}-*.md"))
    if len(matches) != 1:
        raise RuntimeError(
            f"active change {change_id} must resolve to exactly one file; found {len(matches)}"
        )
    return matches[0]


def _validate_release(state: dict[str, Any], errors: list[str]) -> None:
    release = state.get("last_integrated_release") or {}
    commit = str(release.get("commit", ""))
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        errors.append("last_integrated_release.commit must be a full SHA")
        return

    releases = state.get("ledgers", {}).get("releases")
    if not releases:
        errors.append("ledgers.releases is missing")
        return
    release_path = ROOT / releases
    if not release_path.exists():
        errors.append(f"release ledger missing: {releases}")
        return
    payload = read_json(release_path)
    if payload.get("commit") != commit:
        errors.append("release ledger commit does not match PROJECT_STATE release commit")

    head = run_git("rev-parse", "HEAD")
    if not git_commit_exists(commit):
        errors.append(f"release anchor not present in Git history: {commit}")
    elif not git_is_ancestor(commit, head):
        errors.append(f"release anchor is not an ancestor of HEAD: {commit}")


def _validate_freezes(state: dict[str, Any], errors: list[str]) -> None:
    head = run_git("rev-parse", "HEAD")
    for key in ("m4_capture_methodology", "m4_outcome_engine"):
        item = state.get("freezes", {}).get(key) or {}
        commit = str(item.get("commit", ""))
        if not re.fullmatch(r"[0-9a-f]{40}", commit):
            errors.append(f"freeze {key} has invalid commit")
            continue
        if not git_commit_exists(commit):
            errors.append(f"freeze {key} commit missing from Git history: {commit}")
        elif not git_is_ancestor(commit, head):
            errors.append(f"freeze {key} is not an ancestor of HEAD")


def validate() -> tuple[bool, list[str], list[str], dict[str, Any]]:
    errors: list[str] = []
    warnings: list[str] = []

    required = [
        BLUEPRINT_PATH,
        STATE_PATH,
        MILESTONES_PATH,
        DECISIONS_PATH,
        SOURCE_PATH,
        ISSUES_PATH,
    ]
    for path in required:
        if not path.exists():
            errors.append(f"missing required Project OS file: {path.relative_to(ROOT)}")

    if errors:
        return False, errors, warnings, {}

    state = read_json(STATE_PATH)
    milestones = read_json(MILESTONES_PATH)
    decisions = read_json(DECISIONS_PATH)
    source = read_json(SOURCE_PATH)
    issues = read_json(ISSUES_PATH)

    if state.get("schema") != 2:
        errors.append("PROJECT_STATE schema must be 2")
    if state.get("recovery_contract", {}).get("chat_is_authoritative") is not False:
        errors.append("chat_is_authoritative must be false")
    if state.get("recovery_contract", {}).get("important_fact_may_exist_only_in_chat") is not False:
        errors.append("important_fact_may_exist_only_in_chat must be false")
    if state.get("recovery_contract", {}).get("bootstrap_must_fail_on_state_drift") is not True:
        errors.append("bootstrap_must_fail_on_state_drift must be true")

    current = state.get("current") or {}
    milestone_id = current.get("milestone")
    phase_id = current.get("phase")
    milestone_rows = {row.get("id"): row for row in milestones.get("milestones", [])}
    if milestone_id not in milestone_rows:
        errors.append(f"current milestone missing from MILESTONES: {milestone_id}")
    else:
        phases = {row.get("id"): row for row in milestone_rows[milestone_id].get("phases", [])}
        if phase_id not in phases:
            errors.append(f"current phase missing from active milestone: {phase_id}")

    active_change = current.get("active_change")
    if active_change:
        try:
            change_path = _find_change_file(str(active_change))
            change_text = change_path.read_text(encoding="utf-8")
            if f"baseline_head: {state.get('governance_baseline', {}).get('head')}" not in change_text:
                errors.append("active Change baseline_head does not match governance baseline")
            status_match = re.search(r"^status:\\s*([a-z_]+)\\s*$", change_text, re.MULTILINE)
            if not status_match:
                errors.append("active Change has no parseable status")
            elif status_match.group(1) not in ALLOWED_CHANGE_STATUS:
                errors.append(
                    f"active Change has invalid status: {status_match.group(1)}"
                )
        except RuntimeError as exc:
            errors.append(str(exc))

    for rel in state.get("required_specs", []):
        if not (ROOT / rel).exists():
            errors.append(f"required spec missing: {rel}")

    ledger_map = state.get("ledgers") or {}
    for name, rel in ledger_map.items():
        if name == "releases":
            continue
        if not (ROOT / rel).exists():
            errors.append(f"ledger reference missing ({name}): {rel}")

    decision_rows = decisions.get("active", [])
    ids = [row.get("id") for row in decision_rows]
    if len(ids) != len(set(ids)):
        errors.append("duplicate active decision IDs")
    for row in decision_rows:
        source_path = row.get("source")
        if source_path and source_path != "DECISIONS.md" and not (ROOT / source_path).exists():
            errors.append(f"active decision source missing: {source_path}")
        if row.get("status") != "active":
            errors.append(f"DECISION_INDEX active row is not active: {row.get('id')}")

    source_ids: list[str] = []
    for row in source.get("items", []):
        source_ids.append(str(row.get("id")))
        if row.get("status") not in ALLOWED_SOURCE_STATUS:
            errors.append(f"invalid source coverage status: {row.get('id')}={row.get('status')}")
    if len(source_ids) != len(set(source_ids)):
        errors.append("duplicate SOURCE_COVERAGE IDs")

    issue_ids = [row.get("id") for row in issues.get("issues", [])]
    if len(issue_ids) != len(set(issue_ids)):
        errors.append("duplicate OPEN_ISSUES IDs")

    attempts_rel = ledger_map.get("attempts")
    if attempts_rel and active_change:
        attempt_path = ROOT / attempts_rel
        seen_active_attempt = False
        if attempt_path.exists():
            for line_no, raw in enumerate(
                attempt_path.read_text(encoding="utf-8").splitlines(), start=1
            ):
                if not raw.strip():
                    continue
                try:
                    record = json.loads(raw)
                except Exception as exc:
                    errors.append(
                        f"attempt ledger invalid JSON at line {line_no}: {exc}"
                    )
                    continue
                if record.get("change_id") == active_change:
                    seen_active_attempt = True
        if not seen_active_attempt:
            errors.append(f"attempt ledger has no record for active change {active_change}")

    _validate_release(state, errors)
    _validate_freezes(state, errors)

    baseline = str(state.get("governance_baseline", {}).get("head", ""))
    head = run_git("rev-parse", "HEAD")
    if not re.fullmatch(r"[0-9a-f]{40}", baseline):
        errors.append("governance baseline head must be a full SHA")
    elif not git_commit_exists(baseline):
        errors.append(f"governance baseline missing from Git history: {baseline}")
    elif not git_is_ancestor(baseline, head):
        errors.append("governance baseline is not an ancestor of HEAD")

    legacy_context = ROOT / "PROJECT_CONTEXT.md"
    if legacy_context.exists():
        legacy_text = legacy_context.read_text(encoding="utf-8")
        if "当前正在完成 **M5 Phase 23" in legacy_text:
            warnings.append(
                "legacy PROJECT_CONTEXT contains stale current-stage prose; it is historical only under D-065"
            )

    return not errors, errors, warnings, state


def _markdown_json(title: str, payload: Any) -> str:
    return f"## {title}\n\n```json\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n```\n"


def build_resume_pack(state: dict[str, Any]) -> str:
    generated = datetime.now().astimezone().isoformat(timespec="seconds")
    head = run_git("rev-parse", "HEAD")
    branch = run_git("branch", "--show-current", allow_failure=True) or "(detached)"
    release = state["last_integrated_release"]
    release_commit = release["commit"]
    recent = run_git(
        "log", "-12", "--date=short", "--pretty=format:%h %ad %s", allow_failure=True
    )
    delta = run_git(
        "log",
        "--date=short",
        "--pretty=format:%h %ad %s",
        f"{release_commit}..{head}",
        allow_failure=True,
    )
    changed = run_git("diff", "--name-status", f"{release_commit}..{head}", allow_failure=True)

    current = state["current"]
    change_text = ""
    if current.get("active_change"):
        change_text = _find_change_file(current["active_change"]).read_text(encoding="utf-8")

    decisions = read_json(DECISIONS_PATH)
    issues = read_json(ISSUES_PATH)
    source = read_json(SOURCE_PATH)

    parts = [
        "# HT-CN Resume Pack v2 — 项目状态续接包\n",
        "> 本文件由 Project OS v2 动态生成。聊天不是权威状态。恢复后仍需核对 canonical Git/CI。\n",
        f"- generated_at: `{generated}`",
        f"- branch: `{branch}`",
        f"- HEAD: `{head}`",
        f"- last_integrated_release: `{release_commit}`",
        f"- current: **{current['phase']} — {current['title']}**",
        f"- status: `{current['status']}`",
        f"- active_change: `{current.get('active_change')}`",
        f"- next_major_task: **{state['next_major_task']['phase']} — {state['next_major_task']['title']}**\n",
        "## 恢复硬规则\n",
        "1. 先验证 PROJECT_STATE，不从聊天猜项目阶段。\n2. 只读取 state 引用的 active Change / required specs / active decisions / open blockers。\n3. state drift 必须先修复，禁止带着不一致继续核心开发。\n",
        _markdown_json("Machine Current State", state),
        _markdown_json("Active Decision Index", decisions),
        _markdown_json("Open Issues", issues),
        _markdown_json("Source Coverage", source),
        "## Active Change\n\n" + (change_text.strip() or "(none)") + "\n",
        "## Required Specs\n\n" + "\n".join(f"- `{x}`" for x in state.get("required_specs", [])) + "\n",
        "## Recent commits\n\n```text\n" + (recent or "(none)") + "\n```\n",
        "## Commits after last integrated release\n\n```text\n" + (delta or "(none)") + "\n```\n",
        "## Changed files after last integrated release\n\n```text\n" + (changed or "(none)") + "\n```\n",
        "## Blank-session recovery questions\n\n"
        "- 当前 canonical release 是什么？\n"
        "- 当前 Milestone/Phase 与 active Change 是什么？\n"
        "- 当前 Gate / blocker / next major task 是什么？\n"
        "- 哪些 Source/Methodology 冻结不能改？\n"
        "- 最近一次失败/成功尝试是什么？\n"
        "- 最新 CI / Git 状态是否与 PROJECT_STATE 一致？\n"
        "任何一项回答不了，都不得宣称已无损续接。\n",
    ]
    return "\n".join(parts).rstrip() + "\n"


def write_resume(path: Path) -> None:
    ok, errors, warnings, state = validate()
    for warning in warnings:
        print(f"[HT-CN PROJECT OS] WARN: {warning}")
    if not ok:
        for error in errors:
            print(f"[HT-CN PROJECT OS] FATAL: {error}")
        raise RuntimeError("Project OS validation failed")
    if not path.is_absolute():
        path = ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_resume_pack(state), encoding="utf-8")
    print(f"[HT-CN PROJECT OS] resume pack written: {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate HT-CN Project OS v2")
    parser.add_argument("--resume", action="store_true", help="write dynamic resume pack")
    parser.add_argument("--output", type=Path, default=DEFAULT_RESUME)
    args = parser.parse_args()

    ok, errors, warnings, state = validate()
    print("[HT-CN PROJECT OS] state integrity")
    for warning in warnings:
        print(f"[HT-CN PROJECT OS] WARN: {warning}")
    for error in errors:
        print(f"[HT-CN PROJECT OS] FATAL: {error}")
    if not ok:
        return 2

    print(
        "[HT-CN PROJECT OS] READY "
        f"phase={state['current']['phase']} "
        f"change={state['current'].get('active_change')} "
        f"release={state['last_integrated_release']['commit'][:12]}"
    )
    if args.resume:
        path = args.output if args.output.is_absolute() else ROOT / args.output
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(build_resume_pack(state), encoding="utf-8")
        print(f"[HT-CN PROJECT OS] resume pack written: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())