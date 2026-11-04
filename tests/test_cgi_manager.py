"""CgiManager：按端口管理 php-cgi 进程（用假的 subprocess，不真的起进程）。"""

from __future__ import annotations

import pytest


class FakePopen:
    """模拟 subprocess.Popen：记录参数，可手动标记退出。"""

    instances: list["FakePopen"] = []

    def __init__(self, args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.pid = 1000 + len(FakePopen.instances)
        self.returncode = None
        self.terminated = False
        self.killed = False
        FakePopen.instances.append(self)

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminated = True
        self.returncode = 0

    def kill(self):
        self.killed = True
        self.returncode = -9

    def wait(self, timeout=None):
        return self.returncode


@pytest.fixture()
def mgr(sandbox, fake_php, monkeypatch):
    import core.cgi_manager as cm

    FakePopen.instances = []
    monkeypatch.setattr(cm.subprocess, "Popen", FakePopen)
    obj = cm.CgiManager()
    obj._fake = FakePopen
    return obj


def test_start_site_uses_version_port(mgr, sandbox):
    from core.site_manager import SiteManager

    sites = SiteManager()
    site = sites.add("s1", "a.local", 8080, str(sandbox / "w1"), "8.3.36")
    version, port = mgr.start_site(site)
    assert version == "8.3.36"
    assert port == 9803
    assert FakePopen.instances[0].args[-1] == "127.0.0.1:9803"


def test_two_versions_two_ports(mgr, sandbox):
    from core.site_manager import SiteManager

    sites = SiteManager()
    s1 = sites.add("s1", "a.local", 8080, str(sandbox / "w1"), "8.3.36")
    s2 = sites.add("s2", "b.local", 8081, str(sandbox / "w2"), "8.4.27")
    v1, p1 = mgr.start_site(s1)
    v2, p2 = mgr.start_site(s2)
    assert (v1, p1) == ("8.3.36", 9803)
    assert (v2, p2) == ("8.4.27", 9804)
    assert len(FakePopen.instances) == 2


def test_same_version_shares_one_process(mgr, sandbox):
    from core.site_manager import SiteManager

    sites = SiteManager()
    s1 = sites.add("s1", "a.local", 8080, str(sandbox / "w1"), "8.3.36")
    s2 = sites.add("s2", "b.local", 8081, str(sandbox / "w2"), "8.3.36")
    mgr.start_site(s1)
    mgr.start_site(s2)
    assert len(FakePopen.instances) == 1
    assert mgr.running_ports() == [("8.3.36", 9803)]


def test_version_swap_stops_old_process(mgr, sandbox):
    """站点改了 PHP 版本后，旧端口上的进程要停掉，新版本起在自己的端口上。"""
    from core.site_manager import SiteManager

    sites = SiteManager()
    site = sites.add("s1", "a.local", 8080, str(sandbox / "w1"), "8.3.36")
    mgr.start_site(site)
    old = FakePopen.instances[0]
    assert old.args[-1] == "127.0.0.1:9803"

    sites.update("s1", php_version="8.4.27")
    started = mgr.sync_all()

    assert old.terminated, "旧版本的 php-cgi 应被停掉"
    assert started == [("8.4.27", 9804)]
    assert mgr.running_ports() == [("8.4.27", 9804)]


def test_sync_all_reuses_running_process(mgr, sandbox):
    """配置没变时不应重复起进程。"""
    from core.site_manager import SiteManager

    sites = SiteManager()
    sites.add("s1", "a.local", 8080, str(sandbox / "w1"), "8.3.36")
    mgr.sync_all()
    mgr.sync_all()
    assert len(FakePopen.instances) == 1


def test_stop_all_terminates_everything(mgr, sandbox):
    from core.site_manager import SiteManager

    sites = SiteManager()
    s1 = sites.add("s1", "a.local", 8080, str(sandbox / "w1"), "8.3.36")
    s2 = sites.add("s2", "b.local", 8081, str(sandbox / "w2"), "8.4.27")
    mgr.start_site(s1)
    mgr.start_site(s2)
    mgr.stop_all()
    assert mgr.running_ports() == []
    assert all(p.terminated for p in FakePopen.instances)


def test_restart_all_respawns(mgr, sandbox):
    from core.site_manager import SiteManager

    sites = SiteManager()
    sites.add("s1", "a.local", 8080, str(sandbox / "w1"), "8.3.36")
    sites.add("s2", "b.local", 8081, str(sandbox / "w2"), "8.4.27")
    mgr.start_site(sites.get("s1"))
    started = mgr.restart_all()
    assert len(started) == 2
    assert len(FakePopen.instances) == 3  # 旧的 1 个 + 重启后 2 个
    assert mgr.running_ports() == [("8.3.36", 9803), ("8.4.27", 9804)]


def test_alive_reflects_process_state(mgr, sandbox):
    from core.site_manager import SiteManager

    sites = SiteManager()
    site = sites.add("s1", "a.local", 8080, str(sandbox / "w1"), "8.3.36")
    version, port = mgr.start_site(site)
    assert mgr.alive(port) is True
    FakePopen.instances[0].returncode = 1
    assert mgr.alive(port) is False
