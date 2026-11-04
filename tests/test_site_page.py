"""站点页 GUI：列表、配置编辑、php-cgi 启停/重启。"""

from __future__ import annotations

import pytest

pytest.importorskip("PyQt6")

from core.site_manager import SiteManager  # noqa: E402
from gui.site_page import SitePage  # noqa: E402


@pytest.fixture()
def page(qapp, sandbox, fake_php, monkeypatch):
    """造一个站点页，CgiManager 用假的，Nginx 用假的。"""
    import core.cgi_manager as cm

    calls: list = []

    class FakeCgi:
        def cleanup_stale(self):
            calls.append("cleanup_stale")

        def start_site(self, site):
            calls.append(("start_site", site["name"]))
            return (site.get("php", ""), 9803)

        def sync_all(self):
            calls.append("sync_all")
            return [("8.3.36", 9803)]

        def restart_all(self):
            calls.append("restart_all")
            return [("8.3.36", 9803)]

        def stop_all(self):
            calls.append("stop_all")

        def running_ports(self):
            return [("8.3.36", 9803)]

    class FakeNginx:
        def running(self):
            return False

        def start(self):
            calls.append("nginx_start")

        def stop(self):
            calls.append("nginx_stop")

        def reload(self):
            calls.append("nginx_reload")

        def test_config(self):
            return "ok"

    monkeypatch.setattr(cm, "CgiManager", FakeCgi)

    from core.nginx_manager import NginxManager

    monkeypatch.setattr(NginxManager, "__init__", lambda self: None)
    monkeypatch.setattr(NginxManager, "running", lambda self: False)
    monkeypatch.setattr(NginxManager, "start", lambda self: calls.append("nginx_start"))
    monkeypatch.setattr(NginxManager, "stop", lambda self: calls.append("nginx_stop"))
    monkeypatch.setattr(NginxManager, "reload", lambda self: calls.append("nginx_reload"))
    monkeypatch.setattr(NginxManager, "test_config", lambda self: "ok")

    widget = SitePage.__new__(SitePage)
    # SitePage.__init__ 会创建真实的 SiteManager / NginxManager，手工装配更可控
    from PyQt6.QtWidgets import QWidget

    QWidget.__init__(widget)
    widget.php = __import__("core.php_manager", fromlist=["PHPManager"]).PHPManager()
    widget.sites = SiteManager()
    widget.nginx = NginxManager()
    widget.cgi = FakeCgi()
    widget.calls = calls
    return widget


def _build_ui(page):
    """最小化地搭出站点页需要的控件（跳过 __init__ 里的网络/进程调用）。"""
    from PyQt6.QtWidgets import (
        QAbstractItemView,
        QCheckBox,
        QLabel,
        QTableWidget,
        QTextEdit,
        QVBoxLayout,
    )

    page.table = QTableWidget(0, 5)
    page.table.setHorizontalHeaderLabels(["名称", "域名", "端口", "PHP", "fastcgi"])
    page.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    page.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    page.table.itemSelectionChanged.connect(page._load_selected)
    page.conf = QTextEdit()
    page.conf_title = QLabel()
    page.cgi_check = QCheckBox()
    page.cgi_check.setChecked(True)
    page.cgi_info = QLabel()
    layout = QVBoxLayout(page)
    layout.addWidget(page.table)

    # 页面独立于 MainWindow 时 self.window() 拿不到状态栏，用桩代替
    class _StatusBar:
        def showMessage(self, *args):
            pass

    class _Window:
        def statusBar(self):
            return _StatusBar()

    page.window = lambda: _Window()
    page.refresh()


def test_table_shows_fastcgi_port(qapp, sandbox, fake_php, page):
    _build_ui(page)
    page.sites.add("s1", "a.local", 8080, str(sandbox / "w1"), "8.3.36")
    page.sites.add("s2", "b.local", 8081, str(sandbox / "w2"), "8.4.27")
    page.refresh()
    assert page.table.rowCount() == 2
    texts = [page.table.item(r, 4).text() for r in range(2)]
    assert "127.0.0.1:9803" in texts
    assert "127.0.0.1:9804" in texts


def test_sync_conf_fields_updates_cgi_port(qapp, sandbox, fake_php, page):
    _build_ui(page)
    page.sites.add("s1", "a.local", 8080, str(sandbox / "w1"), "8.3.36")
    page.sites.update("s1", php_version="8.4.27")
    page._sync_conf_fields("s1")
    text = page.sites.read_conf("s1")
    assert "fastcgi_pass 127.0.0.1:9804" in text
    assert "# php version: 8.4.27" in text


def test_start_cgi_starts_all_sites(qapp, sandbox, fake_php, page):
    _build_ui(page)
    page.sites.add("s1", "a.local", 8080, str(sandbox / "w1"), "8.3.36")
    page.sites.add("s2", "b.local", 8081, str(sandbox / "w2"), "8.4.27")
    page.start_cgi()
    assert "cleanup_stale" in page.calls
    assert "sync_all" in page.calls


def test_restart_cgi_calls_restart_all(qapp, sandbox, fake_php, page):
    _build_ui(page)
    page.sites.add("s1", "a.local", 8080, str(sandbox / "w1"), "8.3.36")
    page.restart_cgi()
    assert "restart_all" in page.calls


def test_stop_cgi_calls_stop_all(qapp, sandbox, fake_php, page):
    _build_ui(page)
    page.sites.add("s1", "a.local", 8080, str(sandbox / "w1"), "8.3.36")
    page.stop_cgi()
    assert "stop_all" in page.calls


def test_nginx_start_also_starts_cgi(qapp, sandbox, fake_php, page):
    _build_ui(page)
    page.sites.add("s1", "a.local", 8080, str(sandbox / "w1"), "8.3.36")
    page.start()
    assert "cleanup_stale" in page.calls
    assert "sync_all" in page.calls
    assert "nginx_start" in page.calls


def test_nginx_reload_syncs_cgi(qapp, sandbox, fake_php, page):
    _build_ui(page)
    page.sites.add("s1", "a.local", 8080, str(sandbox / "w1"), "8.3.36")
    page.reload()
    assert "nginx_reload" in page.calls
    assert "sync_all" in page.calls
