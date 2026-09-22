from __future__ import annotations

from fastapi.testclient import TestClient

import services.api.main as api_main
from htcn.app.product_supervisor import write_product_supervisor_status
from services.api.main import app


def test_product_status_endpoint_exposes_supervisor_and_release_identity(
    monkeypatch,
    tmp_path,
) -> None:
    status_path = tmp_path / "m9-product-supervisor.json"
    write_product_supervisor_status(
        status_path,
        {
            "schema_version": 1,
            "service": "m9_product_supervisor",
            "status": "healthy",
            "healthy": True,
            "release_identity": {
                "head": "abc123",
                "worktree_clean": True,
                "source": "release_manifest",
            },
            "children": {
                "api": {"status": "running"},
                "web": {"status": "running"},
            },
            "diagnostics_zh": ["产品运行正常。"],
        },
    )
    monkeypatch.setattr(api_main, "PRODUCT_SUPERVISOR_STATUS_PATH", status_path)
    monkeypatch.setattr(api_main, "BACKUP_ROOT", tmp_path / "backups")

    response = TestClient(app).get("/api/product/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["release_identity"]["source"] == "release_manifest"
    assert payload["children"]["api"]["status"] == "running"
