from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any, Iterable, Literal


REAL_CLOSEOUT_PREFLIGHT_SCHEMA_VERSION = 1
PHASE22_MAIN_MERGE = "56b6da0d30b951c3ff569ff4739ddbe6e5d3e695"
MIN_FREE_DISK_BYTES = 1 * 1024**3
RECOMMENDED_FREE_DISK_BYTES = 5 * 1024**3
REQUIRED_PYTHON_MODULES = ("duckdb", "pandas", "pyarrow", "htcn")
REQUIRED_CATALOG_TABLES = (
    "daily_dataset",
    "security_master",
    "sync_task",
    "trade_calendar",
)

CheckSeverity = Literal["blocker", "warning"]


@dataclass(frozen=True, slots=True)
class PreflightCheck:
    name: str
    severity: CheckSeverity
    passed: bool
    detail: str
    data: dict[str, Any]

    def as_payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class RealCloseoutPreflightContract:
    version: int = 1
    semantics: str = "read_only_preflight_before_private_m1_closeout"
    branch_required: str = "main"
    remote_main_exact_match_required: bool = True
    phase22_ancestry_required: bool = True
    tracked_worktree_clean_required: bool = True
    python_313_required: bool = True
    project_venv_required: bool = True
    catalog_opened_read_only: bool = True
    provider_probe_is_read_only: bool = True
    browser_probe_is_ephemeral: bool = True
    auto_git_pull: bool = False
    auto_git_fetch: bool = False
    auto_dependency_install: bool = False
    auto_playwright_install: bool = False
    mutates_m1_market_data: bool = False
    mutates_product_state: bool = False
    writes_m4_evidence: bool = False
    starts_daily_close: bool = False
    starts_phase19_delivery: bool = False
    is_trade_instruction: bool = False

    def as_payload(self) -> dict[str, Any]:
        return asdict(self)


REQUIRED_CHECK_SEVERITY: dict[str, CheckSeverity] = {
    "git_repository": "blocker",
    "branch_main": "blocker",
    "worktree_clean": "blocker",
    "remote_main_reachable": "blocker",
    "remote_main_matches_head": "blocker",
    "phase22_ancestor": "blocker",
    "python_version_313": "blocker",
    "python_from_project_venv": "blocker",
    "python_dependencies": "blocker",
    "m1_catalog_exists": "blocker",
    "m1_catalog_read_only": "blocker",
    "m1_required_tables": "blocker",
    "m1_scope_initialized": "blocker",
    "m1_dataset_metadata_valid": "blocker",
    "m1_parquet_files_present": "blocker",
    "m1_calendar_present": "blocker",
    "m1_full_listed_coverage": "warning",
    "provider_liveness": "blocker",
    "node_available": "blocker",
    "npm_available": "blocker",
    "npx_available": "blocker",
    "npm_dependency_tree": "blocker",
    "playwright_package": "blocker",
    "chromium_executable": "blocker",
    "chromium_launch": "blocker",
    "report_path_writable": "blocker",
    "market_delta_path_writable": "blocker",
    "product_path_writable": "blocker",
    "free_disk_minimum": "blocker",
    "free_disk_recommended": "warning",
}


def make_check(
    name: str,
    *,
    passed: bool,
    detail: str,
    data: dict[str, Any] | None = None,
) -> PreflightCheck:
    if name not in REQUIRED_CHECK_SEVERITY:
        raise ValueError(f"unknown_preflight_check:{name}")
    return PreflightCheck(
        name=name,
        severity=REQUIRED_CHECK_SEVERITY[name],
        passed=bool(passed),
        detail=str(detail),
        data=dict(data or {}),
    )


def evaluate_real_closeout_preflight(
    checks: Iterable[PreflightCheck],
    *,
    root: str | Path | None = None,
    head: str | None = None,
) -> dict[str, Any]:
    items = list(checks)
    by_name = {item.name: item for item in items}
    errors: list[str] = []
    warnings: list[str] = []

    if len(by_name) != len(items):
        errors.append("duplicate_check_name")

    expected = set(REQUIRED_CHECK_SEVERITY)
    actual = set(by_name)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing or extra:
        errors.append(
            "check_set_mismatch:"
            f"missing={','.join(missing)}:"
            f"extra={','.join(extra)}"
        )

    for name in sorted(expected & actual):
        item = by_name[name]
        expected_severity = REQUIRED_CHECK_SEVERITY[name]
        if item.severity != expected_severity:
            errors.append(
                f"check_severity_mismatch:{name}:"
                f"expected={expected_severity}:actual={item.severity}"
            )
            continue
        if item.passed:
            continue
        message = f"{name}:{item.detail}"
        if item.severity == "blocker":
            errors.append(message)
        else:
            warnings.append(message)

    status = "blocked" if errors else ("ready_with_warnings" if warnings else "ready")
    return {
        "schema_version": REAL_CLOSEOUT_PREFLIGHT_SCHEMA_VERSION,
        "status": status,
        "root": str(Path(root).resolve()) if root is not None else None,
        "head": head,
        "contract": RealCloseoutPreflightContract().as_payload(),
        "check_count": len(items),
        "passed_count": sum(item.passed for item in items),
        "blocker_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
        "checks": {
            item.name: item.as_payload()
            for item in sorted(items, key=lambda value: value.name)
        },
        "next_action": (
            "daily_close_and_phase19_may_start"
            if not errors
            else "stop_before_any_m1_or_product_mutation"
        ),
        "authoritative_evidence": False,
        "writes_m4_evidence": False,
        "mutates_product_state": False,
        "is_trade_instruction": False,
    }


def _run(
    command: list[str],
    *,
    cwd: Path,
    timeout: int = 30,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=timeout,
    )


def _git(
    root: Path,
    *args: str,
    timeout: int = 30,
) -> subprocess.CompletedProcess[str]:
    return _run(["git", *args], cwd=root, timeout=timeout)


def _is_project_venv_python(root: Path, executable: str) -> bool:
    actual = str(Path(executable).resolve()).casefold()
    candidates = (
        root / ".venv" / "Scripts" / "python.exe",
        root / ".venv" / "bin" / "python",
    )
    return any(
        actual == str(candidate.resolve()).casefold()
        for candidate in candidates
    )


def _probe_python_dependencies() -> tuple[bool, dict[str, str]]:
    versions: dict[str, str] = {}
    for module_name in REQUIRED_PYTHON_MODULES:
        try:
            module = importlib.import_module(module_name)
        except Exception as exc:
            versions[module_name] = f"ERROR:{type(exc).__name__}:{exc}"
            continue
        version = getattr(module, "__version__", None)
        versions[module_name] = str(version) if version is not None else "import_ok"
    return (
        all(not value.startswith("ERROR:") for value in versions.values()),
        versions,
    )


def _catalog_probe(root: Path) -> dict[str, Any]:
    path = root / "data" / "market" / "catalog.duckdb"
    result: dict[str, Any] = {
        "path": str(path),
        "exists": path.is_file(),
        "read_only_open": False,
        "tables": [],
        "listed_scope_count": 0,
        "initialized_scope_count": 0,
        "invalid_metadata_count": 0,
        "missing_parquet_count": 0,
        "missing_parquet_examples": [],
        "calendar_count": 0,
        "calendar_first": None,
        "calendar_last": None,
        "error": None,
    }
    if not path.is_file():
        return result

    try:
        duckdb = importlib.import_module("duckdb")
        con = duckdb.connect(str(path), read_only=True)
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}:{exc}"
        return result

    try:
        result["read_only_open"] = True
        tables = {
            str(row[0])
            for row in con.execute("SHOW TABLES").fetchall()
        }
        result["tables"] = sorted(tables)
        if not set(REQUIRED_CATALOG_TABLES).issubset(tables):
            return result

        scope_sql = (
            "(instrument_id LIKE 'SSE.%' OR instrument_id LIKE 'SZSE.%')"
        )
        listed_scope_count = int(
            con.execute(
                "SELECT COUNT(*) FROM security_master "
                "WHERE status='listed' AND " + scope_sql
            ).fetchone()[0]
        )
        datasets = con.execute(
            "SELECT instrument_id, parquet_path, row_count, "
            "first_trade_date, last_trade_date "
            "FROM daily_dataset WHERE " + scope_sql
        ).fetchall()
        invalid_metadata = 0
        missing_files: list[str] = []
        for instrument_id, parquet_path, row_count, first_date, last_date in datasets:
            invalid = (
                not parquet_path
                or int(row_count or 0) <= 0
                or first_date is None
                or last_date is None
                or first_date > last_date
            )
            if invalid:
                invalid_metadata += 1
            if parquet_path:
                candidate = Path(str(parquet_path))
                if not candidate.is_absolute():
                    candidate = root / candidate
                if not candidate.is_file() or candidate.stat().st_size <= 0:
                    if len(missing_files) < 20:
                        missing_files.append(
                            f"{instrument_id}:{candidate}"
                        )
        calendar_count, calendar_first, calendar_last = con.execute(
            "SELECT COUNT(*), MIN(trade_date), MAX(trade_date) "
            "FROM trade_calendar"
        ).fetchone()

        result.update(
            {
                "listed_scope_count": listed_scope_count,
                "initialized_scope_count": len(datasets),
                "invalid_metadata_count": invalid_metadata,
                "missing_parquet_count": sum(
                    1
                    for instrument_id, parquet_path, *_ in datasets
                    if parquet_path
                    and not (
                        (Path(str(parquet_path)) if Path(str(parquet_path)).is_absolute()
                         else root / Path(str(parquet_path))).is_file()
                    )
                ),
                "missing_parquet_examples": missing_files,
                "calendar_count": int(calendar_count or 0),
                "calendar_first": (
                    calendar_first.isoformat()
                    if isinstance(calendar_first, date)
                    else str(calendar_first) if calendar_first else None
                ),
                "calendar_last": (
                    calendar_last.isoformat()
                    if isinstance(calendar_last, date)
                    else str(calendar_last) if calendar_last else None
                ),
            }
        )
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}:{exc}"
    finally:
        con.close()
    return result


def _provider_probe(root: Path) -> tuple[bool, str, dict[str, Any]]:
    code = r"""
from datetime import date, timedelta
import json
from htcn.data.providers import AkShareProvider, AkShareSinaProvider, BaoStockProvider, FailoverProvider

provider = FailoverProvider(
    AkShareProvider(),
    FailoverProvider(AkShareSinaProvider(), BaoStockProvider()),
)
end = date.today()
start = end - timedelta(days=21)
days = provider.get_trade_calendar(start, end)
if not days:
    raise RuntimeError("no_trade_calendar_days")
print(json.dumps({
    "trading_day_count": len(days),
    "provider": str(provider.last_provider or provider.name),
    "first": days[0].isoformat(),
    "last": days[-1].isoformat(),
}, sort_keys=True))
"""
    try:
        proc = _run([sys.executable, "-c", code], cwd=root, timeout=45)
    except subprocess.TimeoutExpired:
        return False, "provider_probe_timeout", {}
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip()[-1000:]
        return False, f"provider_probe_failed:{detail}", {}
    try:
        payload = json.loads(proc.stdout.strip().splitlines()[-1])
    except Exception:
        payload = {"stdout": proc.stdout.strip()[-1000:]}
    return True, "provider_trade_calendar_reachable", payload


def _which(name: str) -> str | None:
    return shutil.which(name)


def _node_probe(
    root: Path,
    *,
    node: str | None,
    npm: str | None,
) -> dict[str, Any]:
    web = root / "apps" / "web"
    result: dict[str, Any] = {
        "dependency_tree_ok": False,
        "playwright_package_ok": False,
        "chromium_executable_ok": False,
        "chromium_executable": None,
        "chromium_launch_ok": False,
        "errors": [],
    }
    if npm:
        try:
            proc = _run([npm, "ls", "--depth=0", "--json"], cwd=web, timeout=45)
            result["dependency_tree_ok"] = proc.returncode == 0
            if proc.returncode != 0:
                result["errors"].append(
                    "npm_ls:" + (proc.stderr or proc.stdout).strip()[-1000:]
                )
        except subprocess.TimeoutExpired:
            result["errors"].append("npm_ls_timeout")

    if not node:
        return result

    resolve_code = (
        "const p=require.resolve('@playwright/test/package.json');"
        "process.stdout.write(p);"
    )
    try:
        resolved = _run([node, "-e", resolve_code], cwd=web, timeout=20)
        result["playwright_package_ok"] = resolved.returncode == 0
        if resolved.returncode != 0:
            result["errors"].append(
                "playwright_resolve:"
                + (resolved.stderr or resolved.stdout).strip()[-1000:]
            )
    except subprocess.TimeoutExpired:
        result["errors"].append("playwright_resolve_timeout")

    executable_code = (
        "const fs=require('fs');"
        "const {chromium}=require('@playwright/test');"
        "const p=chromium.executablePath();"
        "process.stdout.write(JSON.stringify({path:p,exists:fs.existsSync(p)}));"
    )
    try:
        executable = _run([node, "-e", executable_code], cwd=web, timeout=20)
        if executable.returncode == 0:
            payload = json.loads(executable.stdout.strip())
            result["chromium_executable"] = payload.get("path")
            result["chromium_executable_ok"] = bool(payload.get("exists"))
        else:
            result["errors"].append(
                "chromium_executable:"
                + (executable.stderr or executable.stdout).strip()[-1000:]
            )
    except (subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        result["errors"].append(f"chromium_executable_probe:{type(exc).__name__}")

    launch_code = r"""
const { chromium } = require('@playwright/test');
(async () => {
  const browser = await chromium.launch({headless: true});
  await browser.close();
  process.stdout.write('ok');
})().catch((error) => {
  console.error(error && error.stack ? error.stack : String(error));
  process.exit(2);
});
"""
    try:
        launched = _run([node, "-e", launch_code], cwd=web, timeout=45)
        result["chromium_launch_ok"] = launched.returncode == 0
        if launched.returncode != 0:
            result["errors"].append(
                "chromium_launch:"
                + (launched.stderr or launched.stdout).strip()[-1000:]
            )
    except subprocess.TimeoutExpired:
        result["errors"].append("chromium_launch_timeout")
    return result


def _path_writable_without_mutation(path: Path) -> tuple[bool, str]:
    candidate = path
    while not candidate.exists() and candidate != candidate.parent:
        candidate = candidate.parent
    if not candidate.exists():
        return False, "no_existing_parent"
    if not candidate.is_dir():
        candidate = candidate.parent
    writable = os.access(candidate, os.W_OK)
    return writable, str(candidate)


def collect_real_closeout_preflight(
    root: str | Path,
) -> tuple[list[PreflightCheck], str | None]:
    root_path = Path(root).resolve()
    checks: list[PreflightCheck] = []

    git_dir = root_path / ".git"
    repo_ok = git_dir.exists()
    checks.append(
        make_check(
            "git_repository",
            passed=repo_ok,
            detail="git_repository_present" if repo_ok else "git_repository_missing",
            data={"git_dir": str(git_dir)},
        )
    )

    branch: str | None = None
    head: str | None = None
    clean = False
    remote_main: str | None = None
    remote_reachable = False
    phase22_ancestor = False
    if repo_ok:
        branch_proc = _git(root_path, "symbolic-ref", "--quiet", "--short", "HEAD")
        head_proc = _git(root_path, "rev-parse", "HEAD")
        status_proc = _git(root_path, "status", "--porcelain")
        branch = branch_proc.stdout.strip() if branch_proc.returncode == 0 else None
        head = head_proc.stdout.strip() if head_proc.returncode == 0 else None
        clean = status_proc.returncode == 0 and not status_proc.stdout.strip()
        try:
            remote = _git(
                root_path,
                "ls-remote",
                "--exit-code",
                "origin",
                "refs/heads/main",
                timeout=30,
            )
            if remote.returncode == 0 and remote.stdout.strip():
                remote_main = remote.stdout.strip().split()[0]
                remote_reachable = len(remote_main) == 40
        except subprocess.TimeoutExpired:
            remote_reachable = False
        if head:
            ancestor = _git(
                root_path,
                "merge-base",
                "--is-ancestor",
                PHASE22_MAIN_MERGE,
                head,
            )
            phase22_ancestor = ancestor.returncode == 0

    checks.extend(
        [
            make_check(
                "branch_main",
                passed=branch == "main",
                detail=f"branch={branch or 'unavailable'}",
                data={"branch": branch},
            ),
            make_check(
                "worktree_clean",
                passed=clean,
                detail="tracked_and_untracked_worktree_clean" if clean else "worktree_dirty",
                data={"clean": clean},
            ),
            make_check(
                "remote_main_reachable",
                passed=remote_reachable,
                detail=(
                    "origin_main_resolved"
                    if remote_reachable
                    else "origin_main_unreachable_or_invalid"
                ),
                data={"remote_main": remote_main},
            ),
            make_check(
                "remote_main_matches_head",
                passed=bool(head and remote_main and head == remote_main),
                detail=(
                    "local_head_equals_origin_main"
                    if head and remote_main and head == remote_main
                    else f"local={head}:remote={remote_main}"
                ),
                data={"head": head, "remote_main": remote_main},
            ),
            make_check(
                "phase22_ancestor",
                passed=phase22_ancestor,
                detail=(
                    "phase22_main_merge_is_ancestor"
                    if phase22_ancestor
                    else "phase22_main_merge_not_ancestor"
                ),
                data={"required_ancestor": PHASE22_MAIN_MERGE},
            ),
        ]
    )

    py_ok = sys.version_info.major == 3 and sys.version_info.minor == 13
    venv_ok = _is_project_venv_python(root_path, sys.executable)
    deps_ok, dep_versions = _probe_python_dependencies()
    checks.extend(
        [
            make_check(
                "python_version_313",
                passed=py_ok,
                detail=f"python={sys.version.split()[0]}",
                data={"executable": sys.executable, "version": sys.version.split()[0]},
            ),
            make_check(
                "python_from_project_venv",
                passed=venv_ok,
                detail=(
                    "project_venv_python"
                    if venv_ok
                    else f"unexpected_python:{sys.executable}"
                ),
                data={"executable": sys.executable},
            ),
            make_check(
                "python_dependencies",
                passed=deps_ok,
                detail="all_required_modules_importable" if deps_ok else "dependency_import_failed",
                data={"modules": dep_versions},
            ),
        ]
    )

    catalog = _catalog_probe(root_path) if deps_ok else {
        "path": str(root_path / "data" / "market" / "catalog.duckdb"),
        "exists": (root_path / "data" / "market" / "catalog.duckdb").is_file(),
        "read_only_open": False,
        "tables": [],
        "listed_scope_count": 0,
        "initialized_scope_count": 0,
        "invalid_metadata_count": 0,
        "missing_parquet_count": 0,
        "missing_parquet_examples": [],
        "calendar_count": 0,
        "calendar_first": None,
        "calendar_last": None,
        "error": "python_dependencies_not_ready",
    }
    tables = set(catalog.get("tables", []))
    listed_scope = int(catalog.get("listed_scope_count") or 0)
    initialized_scope = int(catalog.get("initialized_scope_count") or 0)
    checks.extend(
        [
            make_check(
                "m1_catalog_exists",
                passed=bool(catalog.get("exists")),
                detail="catalog_present" if catalog.get("exists") else "catalog_missing",
                data={"path": catalog.get("path")},
            ),
            make_check(
                "m1_catalog_read_only",
                passed=bool(catalog.get("read_only_open")) and not catalog.get("error"),
                detail=(
                    "catalog_read_only_open_ok"
                    if catalog.get("read_only_open") and not catalog.get("error")
                    else f"catalog_read_failed:{catalog.get('error')}"
                ),
                data={"error": catalog.get("error")},
            ),
            make_check(
                "m1_required_tables",
                passed=set(REQUIRED_CATALOG_TABLES).issubset(tables),
                detail=(
                    "required_tables_present"
                    if set(REQUIRED_CATALOG_TABLES).issubset(tables)
                    else "required_tables_missing"
                ),
                data={
                    "required": list(REQUIRED_CATALOG_TABLES),
                    "actual": sorted(tables),
                },
            ),
            make_check(
                "m1_scope_initialized",
                passed=initialized_scope > 0,
                detail=f"initialized_scope_count={initialized_scope}",
                data={
                    "initialized_scope_count": initialized_scope,
                    "listed_scope_count": listed_scope,
                },
            ),
            make_check(
                "m1_dataset_metadata_valid",
                passed=int(catalog.get("invalid_metadata_count") or 0) == 0,
                detail=(
                    "dataset_metadata_valid"
                    if int(catalog.get("invalid_metadata_count") or 0) == 0
                    else f"invalid_metadata_count={catalog.get('invalid_metadata_count')}"
                ),
                data={
                    "invalid_metadata_count": int(catalog.get("invalid_metadata_count") or 0)
                },
            ),
            make_check(
                "m1_parquet_files_present",
                passed=int(catalog.get("missing_parquet_count") or 0) == 0,
                detail=(
                    "all_catalog_parquet_files_present"
                    if int(catalog.get("missing_parquet_count") or 0) == 0
                    else f"missing_parquet_count={catalog.get('missing_parquet_count')}"
                ),
                data={
                    "missing_parquet_count": int(catalog.get("missing_parquet_count") or 0),
                    "examples": catalog.get("missing_parquet_examples", []),
                },
            ),
            make_check(
                "m1_calendar_present",
                passed=int(catalog.get("calendar_count") or 0) > 0,
                detail=f"calendar_count={catalog.get('calendar_count') or 0}",
                data={
                    "calendar_count": int(catalog.get("calendar_count") or 0),
                    "first": catalog.get("calendar_first"),
                    "last": catalog.get("calendar_last"),
                },
            ),
            make_check(
                "m1_full_listed_coverage",
                passed=(
                    listed_scope > 0
                    and initialized_scope >= listed_scope
                ),
                detail=(
                    "all_listed_sse_szse_initialized"
                    if listed_scope > 0 and initialized_scope >= listed_scope
                    else (
                        "partial_initialized_scope_allowed:"
                        f"{initialized_scope}/{listed_scope}"
                    )
                ),
                data={
                    "listed_scope_count": listed_scope,
                    "initialized_scope_count": initialized_scope,
                    "hard_blocking": False,
                },
            ),
        ]
    )

    if deps_ok:
        provider_ok, provider_detail, provider_data = _provider_probe(root_path)
    else:
        provider_ok, provider_detail, provider_data = (
            False,
            "python_dependencies_not_ready",
            {},
        )
    checks.append(
        make_check(
            "provider_liveness",
            passed=provider_ok,
            detail=provider_detail,
            data=provider_data,
        )
    )

    node = _which("node")
    npm = _which("npm")
    npx = _which("npx")
    checks.extend(
        [
            make_check(
                "node_available",
                passed=bool(node),
                detail=node or "node_not_found",
                data={"path": node},
            ),
            make_check(
                "npm_available",
                passed=bool(npm),
                detail=npm or "npm_not_found",
                data={"path": npm},
            ),
            make_check(
                "npx_available",
                passed=bool(npx),
                detail=npx or "npx_not_found",
                data={"path": npx},
            ),
        ]
    )
    node_probe = _node_probe(root_path, node=node, npm=npm) if node else {
        "dependency_tree_ok": False,
        "playwright_package_ok": False,
        "chromium_executable_ok": False,
        "chromium_executable": None,
        "chromium_launch_ok": False,
        "errors": ["node_not_available"],
    }
    checks.extend(
        [
            make_check(
                "npm_dependency_tree",
                passed=bool(node_probe.get("dependency_tree_ok")),
                detail=(
                    "npm_dependency_tree_ok"
                    if node_probe.get("dependency_tree_ok")
                    else "npm_dependency_tree_not_ready"
                ),
                data={"errors": node_probe.get("errors", [])},
            ),
            make_check(
                "playwright_package",
                passed=bool(node_probe.get("playwright_package_ok")),
                detail=(
                    "playwright_package_resolved"
                    if node_probe.get("playwright_package_ok")
                    else "playwright_package_missing"
                ),
                data={"errors": node_probe.get("errors", [])},
            ),
            make_check(
                "chromium_executable",
                passed=bool(node_probe.get("chromium_executable_ok")),
                detail=(
                    str(node_probe.get("chromium_executable"))
                    if node_probe.get("chromium_executable_ok")
                    else "playwright_chromium_executable_missing"
                ),
                data={
                    "path": node_probe.get("chromium_executable"),
                    "errors": node_probe.get("errors", []),
                },
            ),
            make_check(
                "chromium_launch",
                passed=bool(node_probe.get("chromium_launch_ok")),
                detail=(
                    "headless_chromium_launch_ok"
                    if node_probe.get("chromium_launch_ok")
                    else "headless_chromium_launch_failed"
                ),
                data={"errors": node_probe.get("errors", [])},
            ),
        ]
    )

    writable_targets = {
        "report_path_writable": root_path / "artifacts" / "reports",
        "market_delta_path_writable": root_path / "data" / "market" / "daily_delta",
        "product_path_writable": root_path / "data" / "product" / "m5",
    }
    for check_name, target in writable_targets.items():
        writable, checked_parent = _path_writable_without_mutation(target)
        checks.append(
            make_check(
                check_name,
                passed=writable,
                detail=(
                    f"writable_parent={checked_parent}"
                    if writable
                    else f"not_writable:{checked_parent}"
                ),
                data={
                    "target": str(target),
                    "checked_parent": checked_parent,
                    "probe_created_file": False,
                },
            )
        )

    disk = shutil.disk_usage(root_path)
    checks.extend(
        [
            make_check(
                "free_disk_minimum",
                passed=disk.free >= MIN_FREE_DISK_BYTES,
                detail=f"free_bytes={disk.free}",
                data={
                    "free_bytes": disk.free,
                    "minimum_bytes": MIN_FREE_DISK_BYTES,
                },
            ),
            make_check(
                "free_disk_recommended",
                passed=disk.free >= RECOMMENDED_FREE_DISK_BYTES,
                detail=f"free_bytes={disk.free}",
                data={
                    "free_bytes": disk.free,
                    "recommended_bytes": RECOMMENDED_FREE_DISK_BYTES,
                    "hard_blocking": False,
                },
            ),
        ]
    )
    return checks, head


def write_real_closeout_preflight_report(
    *,
    root: str | Path,
    output: str | Path,
) -> tuple[dict[str, Any], int]:
    root_path = Path(root).resolve()
    checks, head = collect_real_closeout_preflight(root_path)
    payload = evaluate_real_closeout_preflight(
        checks,
        root=root_path,
        head=head,
    )
    output_path = Path(output)
    if not output_path.is_absolute():
        output_path = root_path / output_path
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
                allow_nan=False,
            )
            + "\n",
            encoding="utf-8",
        )
    except Exception as exc:
        payload["status"] = "blocked"
        payload["blocker_count"] = int(payload["blocker_count"]) + 1
        payload["errors"] = list(payload["errors"]) + [
            f"preflight_report_write_failed:{type(exc).__name__}:{exc}"
        ]
        payload["next_action"] = "stop_before_any_m1_or_product_mutation"
        return payload, 2
    return payload, 0 if payload["status"] != "blocked" else 2
