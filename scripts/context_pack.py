from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTEXT_FILE = ROOT / "PROJECT_CONTEXT.md"
DEFAULT_OUTPUT = ROOT / "logs" / "context" / "HTCN_CONTEXT_PACK.md"

CORE_FILES = [
    "AGENTS.md",
    "PROJECT_CONTEXT.md",
    "DECISIONS.md",
    "SESSION_LOG.md",
    "README.md",
]

ACTIVE_SPECS = [
    "specs/m2-source-fidelity-repair.md",
    "specs/m2-book-golden-ledger.md",
    "specs/m2-shark-five-zero.md",
    "specs/m2-30-shark-source-freeze-closeout.md",
    "specs/m3-workbench.md",
]


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
        message = proc.stderr.strip() or proc.stdout.strip() or f"git {' '.join(args)} failed"
        raise RuntimeError(message)
    return proc.stdout.strip()


def read_checkpoint() -> str:
    if not CONTEXT_FILE.exists():
        raise RuntimeError("PROJECT_CONTEXT.md is missing")
    text = CONTEXT_FILE.read_text(encoding="utf-8")
    match = re.search(r"^context_checkpoint:\s*`([0-9a-fA-F]{7,40})`\s*$", text, re.MULTILINE)
    if not match:
        raise RuntimeError("PROJECT_CONTEXT.md has no valid context_checkpoint")
    return match.group(1)


def git_is_ancestor(base: str, head: str) -> bool:
    proc = subprocess.run(
        ["git", "merge-base", "--is-ancestor", base, head],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return proc.returncode == 0


def validate() -> tuple[bool, list[str], dict[str, str]]:
    messages: list[str] = []
    ok = True
    for rel in CORE_FILES:
        if not (ROOT / rel).exists():
            ok = False
            messages.append(f"FATAL: missing {rel}")
    try:
        head = run_git("rev-parse", "HEAD")
        branch = run_git("branch", "--show-current") or "(detached)"
        checkpoint = read_checkpoint()
        run_git("cat-file", "-e", f"{checkpoint}^{{commit}}")
    except Exception as exc:
        return False, [f"FATAL: {exc}"], {}
    ancestor = git_is_ancestor(checkpoint, head)
    if not ancestor:
        ok = False
        messages.append("FATAL: context_checkpoint is not an ancestor of current HEAD")
    status = run_git("status", "--short", allow_failure=True)
    delta_count = run_git("rev-list", "--count", f"{checkpoint}..{head}", allow_failure=True) or "0"
    if status:
        messages.append("WARN: working tree is dirty; generated pack will record the uncommitted paths")
    if delta_count != "0":
        messages.append(f"INFO: context_checkpoint is behind HEAD by {delta_count} commit(s); Bootstrap must inspect the delta before coding")
    else:
        messages.append("OK: context_checkpoint equals current HEAD")
    meta = {"head": head, "branch": branch, "checkpoint": checkpoint, "delta_count": delta_count, "status": status}
    return ok, messages, meta


def code_block(text: str, language: str = "text") -> str:
    return f"```{language}\n{text.rstrip()}\n```\n"


def append_file(parts: list[str], rel: str) -> None:
    path = ROOT / rel
    parts.append(f"## FILE: `{rel}`\n")
    if not path.exists():
        parts.append("**MISSING**\n")
        return
    parts.append(path.read_text(encoding="utf-8").rstrip() + "\n")


def build_pack(meta: dict[str, str]) -> str:
    generated = datetime.now().astimezone().isoformat(timespec="seconds")
    head = meta["head"]
    checkpoint = meta["checkpoint"]
    recent_log = run_git("log", "-15", "--date=short", "--pretty=format:%h %ad %s", allow_failure=True)
    delta_log = run_git("log", "--date=short", "--pretty=format:%h %ad %s", f"{checkpoint}..{head}", allow_failure=True)
    changed = run_git("diff", "--name-status", f"{checkpoint}..{head}", allow_failure=True)
    diff_stat = run_git("diff", "--stat", f"{checkpoint}..{head}", allow_failure=True)
    status = meta.get("status", "")
    parts: list[str] = [
        "# HT-CN Context Pack — 新对话续接包\n",
        "> 用法：新对话先完整读取本文件，再读取/核对仓库当前 HEAD。项目事实以仓库当前状态为准，旧聊天只作历史参考。\n",
        "## Bootstrap Metadata\n",
        f"- generated_at: `{generated}`\n",
        f"- branch: `{meta['branch']}`\n",
        f"- HEAD: `{head}`\n",
        f"- context_checkpoint: `{checkpoint}`\n",
        f"- commits_after_checkpoint: `{meta['delta_count']}`\n",
        "\n",
        "### Working tree\n",
        code_block(status or "clean"),
        "### Recent commits\n",
        code_block(recent_log or "(none)"),
        "### Commits after context checkpoint\n",
        code_block(delta_log or "(none)"),
        "### Changed files after context checkpoint\n",
        code_block(changed or "(none)"),
        "### Diff stat after context checkpoint\n",
        code_block(diff_stat or "(none)"),
        "## 恢复要求\n",
        "在继续实现前，Agent 必须能够说明：当前阶段、当前 Gate、冻结决策、未解决问题、下一步唯一主任务、checkpoint 之后发生了什么、最新测试/CI 状态。若 checkpoint 后有功能提交，应先重新核对相关 specs，再决定是否更新 PROJECT_CONTEXT.md。\n",
    ]
    parts.append("\n# Core Context Files\n")
    for rel in CORE_FILES:
        append_file(parts, rel)
    parts.append("\n# Active Specifications\n")
    for rel in ACTIVE_SPECS:
        append_file(parts, rel)
    return "\n".join(parts).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build/check the HT-CN cross-session context pack")
    parser.add_argument("--check", action="store_true", help="validate continuity metadata only")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="output markdown path")
    args = parser.parse_args()
    ok, messages, meta = validate()
    print("[HT-CN CONTEXT] continuity check")
    for message in messages:
        print(f"[HT-CN CONTEXT] {message}")
    if not ok:
        return 1
    if args.check:
        print("[HT-CN CONTEXT] CHECK PASSED")
        return 0
    output = args.output
    if not output.is_absolute():
        output = ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build_pack(meta), encoding="utf-8")
    print(f"[HT-CN CONTEXT] pack written: {output}")
    print("[HT-CN CONTEXT] Use this file as the first handoff artifact in a new conversation.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
