"""首页：模块卡片信息、快捷操作委托、点卡片跳转信号。"""

from __future__ import annotations

import pytest

pytest.importorskip("PyQt6")

from gui.home_page import HomePage  # noqa: E402


@pytest.fixture()
def pages(qapp, sandbox, fake_php, monkeypatch):
    """五个真实页面 + 首页；NginxManager 用状态 dict 打桩。"""
    import core.nginx_manager as nm
    import gui.hosts_page as gui_hosts
    import gui.log_page as gui_log
    import gui.nginx_page as gui_nginx
    import gui.php_page as gui_php
    import gui.site_page as gui_site

    state = {"installed": True, "running": False}
    monkeypatch.setattr(nm.NginxManager, "running", lambda self: state["running"])
    monkeypatch.setattr(nm.NginxManager, "version", lambda self: "1.31.8")
    monkeypatch.setattr(nm.NginxManager, "installed", lambda self: state["installed"])

    php = gui_php.PhpPage()
    site = gui_site.SitePage(php.mgr)
    nginx = gui_nginx.NginxPage()
    hosts = gui_hosts.HostsPage()
    log = gui_log.LogPage()
    home = HomePage(site, php, nginx, hosts, log)
    home.state_flags = state
    return home


def test_cards_show_summary(pages):
    """卡片显示关键信息：站点数、PHP 当前版本、hosts/日志计数。"""
    pages.refresh()
    assert "0 个站点" in pages.site_card.body.text()
    assert "已安装 2 个" in pages.php_card.body.text()
    assert "条记录" in pages.hosts_card.body.text()
    assert "个日志文件" in pages.log_card.body.text()


def test_nginx_card_states(pages):
    """Nginx 卡：未装时引导文案 + 隐藏启停；已装时版本/状态 + 启停按钮。"""
    pages.state_flags["installed"] = False
    pages.refresh()
    assert "未安装" in pages.nginx_card.body.text()
    assert pages.nginx_toggle.isHidden()

    pages.state_flags["installed"] = True
    pages.state_flags["running"] = False
    pages.refresh()
    assert "1.31.8" in pages.nginx_card.body.text()
    assert "未运行" in pages.nginx_card.body.text()
    assert not pages.nginx_toggle.isHidden()
    assert pages.nginx_toggle.text() == "启动"

    pages.state_flags["running"] = True
    pages.refresh()
    assert "运行中" in pages.nginx_card.body.text()
    assert pages.nginx_toggle.text() == "停止"


def test_toggle_action_delegates(pages, monkeypatch):
    """Nginx 启停按钮委托给 site_page.toggle_nginx（它连带对齐 php-cgi）。"""
    calls = []
    monkeypatch.setattr(pages.site_page, "toggle_nginx", lambda: calls.append("toggle"))
    pages.nginx_toggle.click()
    assert calls == ["toggle"]


def test_reload_and_add_actions_delegate(pages, monkeypatch):
    """站点卡「重载配置」「新增站点」分别委托给 site_page 的同名方法。"""
    calls = []
    monkeypatch.setattr(pages.site_page, "reload", lambda: calls.append("reload"))
    monkeypatch.setattr(pages.site_page, "add", lambda: calls.append("add"))
    for btn in pages.site_card.findChildren(type(pages.add_site_btn)):
        btn.click()
    assert sorted(calls) == ["add", "reload"]


def test_card_click_emits_navigate(pages):
    """点卡片发 navigate 信号并携带目标页。"""
    got = []
    pages.navigate.connect(got.append)
    pages.php_card.clicked.emit()
    pages.hosts_card.clicked.emit()
    assert got == [pages.php_page, pages.hosts_page]
