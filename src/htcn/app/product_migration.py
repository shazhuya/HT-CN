from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CURRENT_PRODUCT_STATE_SCHEMA = 1
STATE_RELATIVE_PATH = Path("data/product/PRODUCT_STATE_VERSION.json")


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temp.replace(path)


def read_product_state_schema(root: str | Path) -> dict[str, Any] | None:
    path = Path(root) / STATE_RELATIVE_PATH
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("product state schema payload must be an object")
    return payload


def _migrate_0_to_1(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    (root / "data/product").mkdir(parents=True, exist_ok=True)
    (root / "data/market/runtime").mkdir(parents=True, exist_ok=True)
    (root / "backups").mkdir(parents=True, exist_ok=True)
    (root / "updates").mkdir(parents=True, exist_ok=True)
    applied = list(payload.get("applied_migrations") or [])
    marker = "0_to_1_initialize_product_runtime"
    if marker not in applied:
        applied.append(marker)
    return {
        "schema_version": 1,
        "applied_migrations": applied,
    }


MIGRATIONS = {
    0: _migrate_0_to_1,
}


def ensure_product_state_schema(root: str | Path) -> dict[str, Any]:
    base = Path(root)
    existing = read_product_state_schema(base)
    if existing is None:
        payload: dict[str, Any] = {
            "schema_version": 0,
            "applied_migrations": [],
        }
    else:
        payload = dict(existing)

    try:
        version = int(payload.get("schema_version", 0))
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid product state schema version") from exc

    if version > CURRENT_PRODUCT_STATE_SCHEMA:
        raise RuntimeError(
            f"future product state schema {version} > supported {CURRENT_PRODUCT_STATE_SCHEMA}"
        )
    while version < CURRENT_PRODUCT_STATE_SCHEMA:
        migration = MIGRATIONS.get(version)
        if migration is None:
            raise RuntimeError(f"missing product migration from schema {version}")
        payload = migration(base, payload)
        version = int(payload["schema_version"])

    _atomic_write(base / STATE_RELATIVE_PATH, payload)
    return payload
