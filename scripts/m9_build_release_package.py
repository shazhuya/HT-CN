from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from htcn.app.evidence_identity import read_code_identity
from htcn.app.release_package import build_release_package, verify_release_package

ROOT = Path(__file__).resolve().parents[1]


def _guard_payload(script: str) -> dict[str, Any]:
    process = subprocess.run(
        [sys.executable, str(ROOT / script)],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    try:
        payload = json.loads(process.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{script} did not emit JSON: {exc}") from exc
    if process.returncode != 0 or payload.get("status") != "frozen_match":
        raise RuntimeError(f"{script} failed release attestation: {payload}")
    return payload


def _verify_packaged_runtime(package: Path) -> dict[str, object]:
    verification = verify_release_package(package)
    if not verification.get("verified"):
        raise RuntimeError(f"release package verification failed: {verification}")
    results: dict[str, object] = {}
    with tempfile.TemporaryDirectory(prefix="htcn-packaged-runtime-") as temp:
        stage = Path(temp)
        with zipfile.ZipFile(package, "r") as archive:
            archive.extractall(stage)
        if (stage / ".git").exists():
            raise RuntimeError("release package unexpectedly contains .git")
        env = dict(os.environ)
        env["PYTHONPATH"] = str(stage / "src") + (
            os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else ""
        )
        commands = {
            "m4_methodology": [sys.executable, "scripts/m4_methodology_freeze_guard.py"],
            "m4_outcome_engine": [sys.executable, "scripts/m4_outcome_engine_freeze_guard.py"],
            "product_preflight": [sys.executable, "scripts/m9_product_supervisor.py", "--check"],
        }
        for name, command in commands.items():
            process = subprocess.run(
                command,
                cwd=stage,
                env=env,
                text=True,
                encoding="utf-8",
                errors="replace",
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            results[name] = {
                "exit_code": process.returncode,
                "output_tail": process.stdout[-2000:],
            }
            if process.returncode != 0:
                raise RuntimeError(
                    f"packaged runtime check failed: {name}: {process.stdout[-2000:]}"
                )
    return {
        "status": "success",
        "git_present": False,
        "checks": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build verified HT-CN product release package")
    parser.add_argument("--head", default=None)
    parser.add_argument("--output", default=None)
    parser.add_argument(
        "--report",
        default="artifacts/reports/m9-release-package.json",
    )
    args = parser.parse_args()

    identity = read_code_identity(ROOT)
    head = str(args.head or identity.head or "").strip()
    if not head:
        raise RuntimeError("clean Git release HEAD is required")
    if identity.source != "git" or not identity.worktree_clean or identity.head != head:
        raise RuntimeError(
            "release package must be built from the exact clean Git checkout "
            f"(source={identity.source}, head={identity.head}, clean={identity.worktree_clean})"
        )

    methodology = _guard_payload("scripts/m4_methodology_freeze_guard.py")
    outcome = _guard_payload("scripts/m4_outcome_engine_freeze_guard.py")
    attestations = {
        "m4_methodology": methodology,
        "m4_outcome_engine": outcome,
    }
    output = Path(
        args.output
        or f"artifacts/release/htcn-{head[:12]}.zip"
    )
    payload = build_release_package(
        root=ROOT,
        output=output,
        release_head=head,
        attestations=attestations,
    )
    verification = verify_release_package(output)
    if not verification.get("verified"):
        raise RuntimeError(f"release package verification failed: {verification}")
    payload["verification"] = verification
    payload["packaged_runtime_validation"] = _verify_packaged_runtime(output)

    report = Path(args.report)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
