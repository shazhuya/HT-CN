from __future__ import annotations

import importlib.util
import json
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def modules():
    verifier = load_module(
        "htcn_chat_bundle_verifier",
        ROOT / "scripts" / "verify_chat_continuation_bundle.py",
    )
    builder = load_module(
        "htcn_chat_bundle_builder",
        ROOT / "scripts" / "build_chat_continuation_bundle.py",
    )
    return builder, verifier


def build_fixture(tmp_path: Path):
    builder, verifier = modules()
    bundle = tmp_path / "bundle.zip"
    handoff = tmp_path / "handoff.md"
    prompt = tmp_path / "prompt.md"
    manifest = builder.build_bundle(
        bundle,
        handoff,
        prompt,
        require_clean=False,
    )
    return bundle, handoff, prompt, manifest, verifier


def test_portable_chat_bundle_builds_and_verifies(tmp_path: Path) -> None:
    bundle, handoff, prompt, manifest, verifier = build_fixture(tmp_path)
    report = verifier.verify_bundle(bundle)
    assert report["status"] == "valid"
    assert manifest["privacy"]["raw_private_m1_included"] is False
    assert manifest["privacy"]["chat_history_included"] is False
    assert handoff.exists()
    assert handoff.with_suffix(".sha256").exists()
    assert "Bootstrap Receipt" in prompt.read_text(encoding="utf-8")


def test_bundle_contains_current_authority_and_required_specs(tmp_path: Path) -> None:
    bundle, _, _, manifest, _ = build_fixture(tmp_path)
    names = {row["path"] for row in manifest["entries"]}
    state = json.loads((ROOT / "governance" / "PROJECT_STATE.json").read_text(encoding="utf-8"))
    assert "canonical/AGENTS.md" in names
    assert "canonical/CHAT_CONTINUATION.md" in names
    assert "canonical/governance/attempts/2026-09.jsonl" in names
    assert "canonical/governance/PRODUCT_COMPLETION_POLICY.json" in names
    assert all(f"canonical/{path}" in names for path in state["required_specs"])
    with zipfile.ZipFile(bundle) as archive:
        prompt = archive.read("HTCN_NEW_CHAT_PROMPT.md").decode("utf-8")
    assert "不要立即改代码" in prompt
    assert "不需要通读全部旧聊天" in prompt


def test_bundle_rejects_unlisted_member(tmp_path: Path) -> None:
    bundle, _, _, _, verifier = build_fixture(tmp_path)
    with zipfile.ZipFile(bundle, "a") as archive:
        archive.writestr("unexpected.txt", b"tamper")
    with pytest.raises(verifier.BundleVerificationError, match="member set mismatch"):
        verifier.verify_bundle(bundle)


def test_bundle_rejects_duplicate_member(tmp_path: Path) -> None:
    bundle, _, _, _, verifier = build_fixture(tmp_path)
    with (
        pytest.warns(UserWarning, match="Duplicate name"),
        zipfile.ZipFile(bundle, "a") as archive,
    ):
        archive.writestr("START_HERE.md", b"tamper")
    with pytest.raises(verifier.BundleVerificationError, match="duplicate ZIP members"):
        verifier.verify_bundle(bundle)


def test_bundle_rejects_hash_tamper(tmp_path: Path) -> None:
    bundle, _, _, _, verifier = build_fixture(tmp_path)
    rebuilt = tmp_path / "tampered.zip"
    with zipfile.ZipFile(bundle) as source, zipfile.ZipFile(rebuilt, "w") as target:
        for info in source.infolist():
            payload = source.read(info.filename)
            if info.filename == "START_HERE.md":
                payload += b"tamper"
            target.writestr(info.filename, payload)
    with pytest.raises(verifier.BundleVerificationError, match="size mismatch"):
        verifier.verify_bundle(rebuilt)



def test_start_here_does_not_assign_daily_private_m1_as_default_human_action(
    tmp_path: Path,
) -> None:
    bundle, _, _, _, _ = build_fixture(tmp_path)
    with zipfile.ZipFile(bundle) as archive:
        start_here = archive.read("START_HERE.md").decode("utf-8")
        prompt = archive.read("HTCN_NEW_CHAT_PROMPT.md").decode("utf-8")
    assert "development mainline: `M9`" in start_here
    assert "background evidence track: `M7`" in start_here
    assert "user computer is not routine project infrastructure" in start_here
    assert "13 个问题" in prompt
    assert "产品开发默认沿 M9 主线推进" in prompt
