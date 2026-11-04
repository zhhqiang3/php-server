"""主窗口与外观：主题/字体切换、各页签刷新。"""

from __future__ import annotations

import pytest

pytest.importorskip("PyQt6")

from core.paths import load_config  # noqa: E402
from gui.appearance import (  # noqa: E402
    THEMES,
    apply_appearance,
    current_font_size,
    current_theme,
    save_appearance,
)


def test_theme_and_font_roundtrip(sandbox):
    save_appearance("深色", 14)
    assert current_theme() == "深色"
    assert current_font_size() == 14
    save_appearance("浅色", 10)
    assert current_theme() == "浅色"


def test_apply_appearance_sets_font(qapp, sandbox):
    apply_appearance(qapp, theme="深色", font_size=16)
    assert qapp.font().pointSize() == 16


def test_apply_appearance_reads_config(qapp, sandbox):
    save_appearance("浅色", 12)
    apply_appearance(qapp)
    assert qapp.font().pointSize() == 12


def test_theme_names_cover_system(qapp, sandbox):
    assert "跟随系统" in THEMES
    assert "深色" in THEMES
    assert "浅色" in THEMES


def test_main_window_builds(qapp, sandbox, fake_php, monkeypatch):
    """主窗口能构建，且六个页签都在。"""
    import core.nginx_manager as nm

    monkeypatch.setattr(nm.NginxManager, "running", lambda self: False)
    monkeypatch.setattr(nm.NginxManager, "version", lambda self: None)
    monkeypatch.setattr(nm.NginxManager, "installed", lambda self: False)

    from gui.main import MainWindow

    win = MainWindow()
    tabs = win.centralWidget()
    assert tabs.count() == 6
    titles = [tabs.tabText(i) for i in range(tabs.count())]
    assert titles == ["站点", "PHP", "php.ini", "Nginx", "Hosts", "日志"]


def test_ini_tab_hidden_by_default(qapp, sandbox, fake_php, monkeypatch):
    """php.ini 页默认不显示，只从 PHP 列表进入。"""
    import core.nginx_manager as nm

    monkeypatch.setattr(nm.NginxManager, "running", lambda self: False)
    monkeypatch.setattr(nm.NginxManager, "version", lambda self: None)
    monkeypatch.setattr(nm.NginxManager, "installed", lambda self: False)

    from gui.main import MainWindow

    win = MainWindow()
    tabs = win.centralWidget()
    ini_idx = win._index_of(tabs, win.ini_page)
    assert ini_idx >= 0
    assert tabs.isTabVisible(ini_idx) is False
    # 可见页签里没有 php.ini
    visible = [tabs.tabText(i) for i in range(tabs.count()) if tabs.isTabVisible(i)]
    assert "php.ini" not in visible


def test_view_ini_navigates_to_ini_page(qapp, sandbox, fake_php, monkeypatch):
    """PHP 列表点「查看配置」跳到 php.ini 页并定位版本。"""
    import core.nginx_manager as nm

    monkeypatch.setattr(nm.NginxManager, "running", lambda self: False)
    monkeypatch.setattr(nm.NginxManager, "version", lambda self: None)
    monkeypatch.setattr(nm.NginxManager, "installed", lambda self: False)

    from gui.main import MainWindow

    win = MainWindow()
    tabs = win.centralWidget()
    win.show_ini("8.4.27")
    assert tabs.currentIndex() == win._index_of(tabs, win.ini_page)
    assert win.ini_page.version.currentText() == "8.4.27"


def test_ini_back_returns_to_php(qapp, sandbox, fake_php, monkeypatch):
    import core.nginx_manager as nm

    monkeypatch.setattr(nm.NginxManager, "running", lambda self: False)
    monkeypatch.setattr(nm.NginxManager, "version", lambda self: None)
    monkeypatch.setattr(nm.NginxManager, "installed", lambda self: False)

    from gui.main import MainWindow

    win = MainWindow()
    tabs = win.centralWidget()
    win.show_ini("8.4.27")
    win.show_php()
    assert tabs.currentIndex() == win._index_of(tabs, win.php_page)


def test_main_window_switch_theme(qapp, sandbox, fake_php, monkeypatch):
    import core.nginx_manager as nm

    monkeypatch.setattr(nm.NginxManager, "running", lambda self: False)
    monkeypatch.setattr(nm.NginxManager, "version", lambda self: None)
    monkeypatch.setattr(nm.NginxManager, "installed", lambda self: False)

    from gui.main import MainWindow

    win = MainWindow()
    win._set_theme("深色")
    assert load_config()["ui"]["theme"] == "深色"
    win._set_font_size(14)
    assert load_config()["ui"]["font_size"] == 14
