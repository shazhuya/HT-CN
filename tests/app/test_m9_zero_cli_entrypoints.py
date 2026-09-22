from pathlib import Path

from scripts.m9_product_supervisor import child_specs

ROOT = Path(__file__).resolve().parents[2]


def test_daily_start_uses_single_background_supervisor_not_dev_terminals() -> None:
    start = (ROOT / "启动HT-CN.bat").read_text(encoding="utf-8")
    assert "m9_product_supervisor.py" in start
    assert "pythonw.exe" in start
    assert "npm run dev" not in start
    assert "cmd /k" not in start
    assert "uvicorn" not in start


def test_packaged_install_does_not_require_playwright_or_node_when_dist_exists() -> None:
    install = (ROOT / "安装HT-CN.bat").read_text(encoding="utf-8")
    assert 'if not exist "apps\\web\\dist\\index.html"' in install
    assert "npx playwright" not in install
    assert "npm run build" in install


def test_supervisor_serves_built_static_web_and_owns_all_product_children() -> None:
    specs = {item.name: item for item in child_specs()}
    assert set(specs) == {
        "api",
        "web",
        "market_data",
        "harmonic_runtime",
        "background_evidence",
    }
    web = " ".join(specs["web"].command)
    assert "http.server" in web
    assert "apps/web/dist" in web.replace("\\", "/")
    assert "vite" not in web.lower()
    assert "npm" not in web.lower()


def test_zero_cli_recovery_entrypoints_exist() -> None:
    for name in (
        "停止HT-CN.bat",
        "备份HT-CN.bat",
        "恢复HT-CN.bat",
        "更新HT-CN.bat",
    ):
        assert (ROOT / name).is_file()
