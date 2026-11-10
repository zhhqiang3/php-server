"""pytest 公共夹具：隔离的临时数据目录，避免污染真实的 data/ 与 config.yaml。"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture()
def sandbox(tmp_path, monkeypatch):
    """把 core.paths 的 ROOT / CONFIG_PATH 指到临时目录，并重载相关模块。

    连 gui 里持有 core 模块引用的页面一起 reload，否则 GUI 模块里
    `from core.xxx import Y` 拿到的还是旧类，monkeypatch 打不中。
    """
    import core.paths as paths

    monkeypatch.setattr(paths, "ROOT", tmp_path)
    monkeypatch.setattr(paths, "CONFIG_PATH", tmp_path / "config" / "config.yaml")

    import core.php_manager as php_manager
    import core.site_manager as site_manager
    import core.ini_editor as ini_editor
    import core.hosts_manager as hosts_manager
    import core.log_manager as log_manager
    import core.nginx_manager as nginx_manager
    import core.cgi_manager as cgi_manager

    modules = [
        php_manager,
        site_manager,
        ini_editor,
        hosts_manager,
        log_manager,
        nginx_manager,
        cgi_manager,
    ]
    for mod in modules:
        importlib.reload(mod)

    # GUI 模块引用了 core 类，一并 reload 让它们绑定到新类
    import gui.appearance as gui_appearance
    import gui.home_page as gui_home
    import gui.hosts_page as gui_hosts
    import gui.ini_page as gui_ini
    import gui.log_page as gui_log
    import gui.nginx_page as gui_nginx
    import gui.php_page as gui_php
    import gui.site_dialog as gui_site_dialog
    import gui.site_page as gui_site
    import gui.widgets as gui_widgets

    gui_modules = [
        gui_php,
        gui_site,
        gui_site_dialog,
        gui_ini,
        gui_nginx,
        gui_home,
        gui_hosts,
        gui_log,
        gui_appearance,
        gui_widgets,
    ]
    for mod in gui_modules:
        importlib.reload(mod)

    yield tmp_path
    for mod in modules + gui_modules:
        importlib.reload(mod)


@pytest.fixture()
def fake_php(tmp_path, monkeypatch):
    """造几个假的 PHP 版本目录（php.exe / php-cgi.exe / php.ini）。"""
    versions = tmp_path / "data" / "versions"
    made = {}
    for ver in ("8.3.36", "8.4.27"):
        d = versions / ver
        d.mkdir(parents=True)
        (d / "php.exe").write_text("", encoding="utf-8")
        (d / "php-cgi.exe").write_text("", encoding="utf-8")
        (d / "php.ini").write_text(
            "extension_dir = \"ext\"\nmemory_limit = 128M\n;extension=curl\n", encoding="utf-8"
        )
        made[ver] = d
    return made


# ---------- GUI 专用 ----------

@pytest.fixture(scope="session")
def qapp():
    pytest.importorskip("PyQt6")
    from PyQt6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def no_modal_dialogs(monkeypatch):
    """把 QMessageBox 的静态方法打桩，避免测试弹窗阻塞。"""
    from PyQt6.QtWidgets import QMessageBox

    monkeypatch.setattr(
        QMessageBox, "information", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
    )
    monkeypatch.setattr(
        QMessageBox, "warning", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
    )
    monkeypatch.setattr(
        QMessageBox, "critical", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
    )
    monkeypatch.setattr(
        QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
    )


@pytest.fixture()
def stub_window(monkeypatch):
    """页面在测试里没有主窗口，给 window() 装一个带 statusBar 的桩。"""

    class _StatusBar:
        def __init__(self):
            self.messages: list[str] = []

        def showMessage(self, text, *args):
            self.messages.append(text)

    class _Window:
        def __init__(self):
            self._bar = _StatusBar()

        def statusBar(self):
            return self._bar

    window = _Window()
    monkeypatch.setattr(
        "PyQt6.QtWidgets.QWidget.window", lambda self, *a: window, raising=False
    )
    return window
