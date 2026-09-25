from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def test_windows_source_install_binds_web_build_to_git_head() -> None:
    install = _read("安装HT-CN.bat")

    assert 'git rev-parse HEAD' in install
    assert 'apps\\web\\dist\\.htcn-build-head' in install
    assert 'HTCN_NEED_WEB_BUILD' in install
    assert 'npm ci' in install
    assert 'npm run build' in install
    assert 'echo !HTCN_GIT_HEAD!' in install


def test_windows_startup_rejects_stale_source_web_bundle() -> None:
    startup = _read("启动HT-CN.bat")

    assert 'git rev-parse HEAD' in startup
    assert 'apps\\web\\dist\\.htcn-build-head' in startup
    assert 'HTCN_NEED_INSTALL' in startup
    assert 'if /I not "!HTCN_BUILT_HEAD!"=="!HTCN_GIT_HEAD!"' in startup
    assert 'call "安装HT-CN.bat"' in startup


def test_release_without_git_keeps_existing_zero_node_startup_contract() -> None:
    install = _read("安装HT-CN.bat")
    startup = _read("启动HT-CN.bat")

    # Git-head freshness logic is explicitly guarded by .git. A packaged release
    # therefore continues to use its already-built Web assets without Node.
    assert 'if exist ".git" (' in install
    assert 'if exist ".git" (' in startup
    assert 'if not exist "apps\\web\\dist\\index.html"' in startup
