"""系统 hosts 管理：标记块的增删与保留。"""

from __future__ import annotations

import pytest


@pytest.fixture()
def hosts_file(tmp_path):
    p = tmp_path / "hosts"
    p.write_text(
        "127.0.0.1 localhost\n# 原有注释\n192.168.1.1 router.local\n", encoding="utf-8"
    )
    return p


@pytest.fixture()
def mgr(sandbox, hosts_file):
    from core.hosts_manager import HostsManager
    from core.paths import save_config

    save_config({"hosts": {"path": str(hosts_file)}})
    return HostsManager()


def test_entries_empty_at_start(mgr):
    assert mgr.entries() == []


def test_add_appends_block(mgr, hosts_file):
    mgr.add("127.0.0.1", "a.local")
    assert mgr.entries() == [("127.0.0.1", "a.local")]
    text = hosts_file.read_text(encoding="utf-8")
    assert "# BEGIN php-server" in text
    assert "# END php-server" in text


def test_add_keeps_original_lines(mgr, hosts_file):
    mgr.add("127.0.0.1", "a.local")
    text = hosts_file.read_text(encoding="utf-8")
    assert "127.0.0.1 localhost" in text
    assert "192.168.1.1 router.local" in text
    assert "# 原有注释" in text


def test_add_same_host_replaces(mgr):
    mgr.add("127.0.0.1", "a.local")
    mgr.add("10.0.0.1", "a.local")
    assert mgr.entries() == [("10.0.0.1", "a.local")]


def test_remove_host(mgr):
    mgr.add("127.0.0.1", "a.local")
    mgr.add("127.0.0.1", "b.local")
    mgr.remove("a.local")
    assert mgr.entries() == [("127.0.0.1", "b.local")]


def test_remove_missing_host_is_noop(mgr):
    mgr.add("127.0.0.1", "a.local")
    mgr.remove("zzz.local")
    assert mgr.entries() == [("127.0.0.1", "a.local")]


def test_empty_values_rejected(mgr):
    with pytest.raises(ValueError):
        mgr.add("", "a.local")
    with pytest.raises(ValueError):
        mgr.add("127.0.0.1", "  ")


def test_backup_created(mgr, hosts_file):
    mgr.add("127.0.0.1", "a.local")
    backups = list(hosts_file.parent.glob("hosts.bak-*"))
    assert backups, "应当生成 hosts 备份"


def test_contains_finds_any_domain(mgr, hosts_file):
    """不限于本工具的标记段，文件里任何地方出现都算存在。"""
    hosts_file.write_text(
        "127.0.0.1 localhost\n10.0.0.5 other.local\n", encoding="utf-8"
    )
    assert mgr.contains("other.local") is True
    assert mgr.contains("missing.local") is False


def test_contains_ignores_case(mgr, hosts_file):
    mgr.add("127.0.0.1", "MySite.local")
    assert mgr.contains("mysite.local") is True


def test_ensure_adds_when_missing(mgr, hosts_file):
    assert mgr.ensure("127.0.0.1", "new.local") is True
    assert mgr.contains("new.local") is True


def test_ensure_skips_existing(mgr, hosts_file):
    mgr.ensure("127.0.0.1", "new.local")
    assert mgr.ensure("127.0.0.1", "new.local") is False
    assert hosts_file.read_text(encoding="utf-8").count("new.local") == 1
