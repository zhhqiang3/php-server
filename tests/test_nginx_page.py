"""Nginx 页：安装/卸载两态切换、启动停止共用按钮。"""

from __future__ import annotations

import pytest

pytest.importorskip("PyQt6")

from gui.nginx_page import NginxPage  # noqa: E402


@pytest.fixture()
def page(qapp, sandbox, fake_php, monkeypatch):
    import core.nginx_manager as nm

    # installed/running 用 dict 是为了在测试里动态改状态
    state = {"installed": False, "running": False}
    calls: list = []

    def _init(self):
        self.sites = None
        self.prefix = sandbox / "data" / "nginx"
        (self.prefix).mkdir(parents=True, exist_ok=True)

    def _installed(self):
        return state["installed"]

    def _running(self):
        return state["installed"] and state["running"]

    def _toggle(self):
        if state["installed"] and state["running"]:
            calls.append("stop")
            state["running"] = False
        elif state["installed"]:
            calls.append("start")
            state["running"] = True

    monkeypatch.setattr(nm.NginxManager, "__init__", _init)
    monkeypatch.setattr(nm.NginxManager, "installed", _installed)
    monkeypatch.setattr(nm.NginxManager, "running", _running)
    monkeypatch.setattr(nm.NginxManager, "version", lambda self: "1.31.8" if state["installed"] else None)
    monkeypatch.setattr(nm.NginxManager, "start", lambda self: _toggle(self))
    monkeypatch.setattr(nm.NginxManager, "stop", lambda self: _toggle(self))
    monkeypatch.setattr(nm.NginxManager, "reload", lambda self: calls.append("reload"))
    monkeypatch.setattr(nm.NginxManager, "test_config", lambda self: "ok")

    def _uninstall(self, keep_sites=True):
        calls.append("uninstall")
        state["installed"] = False
        state["running"] = False

    monkeypatch.setattr(nm.NginxManager, "uninstall", _uninstall)

    widget = NginxPage()
    widget.state_flags = state
    widget.calls = calls
    return widget


def test_not_installed_shows_install_ui(page):
    """未安装时只显示安装交互，管理区隐藏。"""
    page.state_flags["installed"] = False
    page.refresh()
    assert page.install_widget.isVisible() or not page.install_widget.isHidden()
    assert page.manage_widget.isHidden()


def test_installed_shows_manage_ui(page):
    """安装后隐藏安装区，显示运行管理与卸载。"""
    page.state_flags["installed"] = True
    page.refresh()
    assert page.install_widget.isHidden()
    assert page.manage_widget.isVisible() or not page.manage_widget.isHidden()
    assert page.uninstall_btn is not None


def test_toggle_button_follows_state(page):
    page.state_flags["installed"] = True
    page.state_flags["running"] = False
    page.refresh()
    assert page.toggle_btn.text() == "启动"
    assert page.toggle_btn.property("role") == "primary"

    page.state_flags["running"] = True
    page.refresh()
    assert page.toggle_btn.text() == "停止"
    assert page.toggle_btn.property("role") == "danger"


def test_toggle_run_starts_when_stopped(page):
    page.state_flags["installed"] = True
    page.state_flags["running"] = False
    page.calls.clear()
    page.toggle_run()
    assert page.calls == ["start"]


def test_toggle_run_stops_when_running(page):
    page.state_flags["installed"] = True
    page.state_flags["running"] = True
    page.calls.clear()
    page.toggle_run()
    assert page.calls == ["stop"]


def test_uninstall_asks_and_uninstalls(page, monkeypatch):
    from PyQt6.QtWidgets import QMessageBox

    monkeypatch.setattr(
        QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
    )
    page.state_flags["installed"] = True
    page.calls.clear()
    page.uninstall()
    assert page.calls == ["uninstall"]
    page.state_flags["installed"] = False
    page.refresh()
    assert page.install_widget.isVisible() or not page.install_widget.isHidden()


def test_uninstall_cancelled(page, monkeypatch):
    from PyQt6.QtWidgets import QMessageBox

    monkeypatch.setattr(
        QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.No)
    )
    page.state_flags["installed"] = True
    page.calls.clear()
    page.uninstall()
    assert page.calls == []
