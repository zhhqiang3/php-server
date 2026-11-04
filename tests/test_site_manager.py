"""站点管理：增删改、配置片段生成、多版本 fastcgi 端口。"""

from __future__ import annotations

import json

import pytest

from core.site_manager import SiteManager


@pytest.fixture()
def mgr(sandbox):
    return SiteManager()


def test_add_creates_meta_and_conf(mgr, tmp_path):
    root = tmp_path / "www"
    site = mgr.add("s1", "a.local", 8080, str(root), "8.3.36")
    assert site["php"] == "8.3.36"
    assert (mgr.sites_dir / "s1" / "site.json").exists()
    assert mgr.conf_path("s1").exists()
    assert (root / "index.php").exists()


def test_add_rejects_duplicate_name(mgr, tmp_path):
    mgr.add("s1", "a.local", 8080, str(tmp_path / "w1"), "8.3.36")
    with pytest.raises(FileExistsError):
        mgr.add("s1", "b.local", 8081, str(tmp_path / "w2"), "8.3.36")


def test_add_rejects_duplicate_port(mgr, tmp_path):
    mgr.add("s1", "a.local", 8080, str(tmp_path / "w1"), "8.3.36")
    with pytest.raises(ValueError):
        mgr.add("s2", "b.local", 8080, str(tmp_path / "w2"), "8.3.36")


def test_add_rejects_bad_name(mgr, tmp_path):
    with pytest.raises(ValueError):
        mgr.add("bad/name", "a.local", 8080, str(tmp_path / "w"), "8.3.36")


def test_update_changes_meta(mgr, tmp_path):
    mgr.add("s1", "a.local", 8080, str(tmp_path / "w1"), "8.3.36")
    site = mgr.update("s1", php_version="8.4.27", port=8081)
    assert site["php"] == "8.4.27"
    assert site["port"] == 8081
    assert json.loads((mgr.sites_dir / "s1" / "site.json").read_text(encoding="utf-8"))["php"] == "8.4.27"


def test_update_missing_site_raises(mgr):
    with pytest.raises(FileNotFoundError):
        mgr.update("nope", host="x")


def test_remove_deletes_site(mgr, tmp_path):
    mgr.add("s1", "a.local", 8080, str(tmp_path / "w1"), "8.3.36")
    mgr.remove("s1")
    assert not (mgr.sites_dir / "s1").exists()
    assert mgr.list_sites() == []


def test_server_block_uses_version_port(mgr, tmp_path):
    site = mgr.add("s1", "a.local", 8080, str(tmp_path / "w1"), "8.4.27")
    block = mgr.server_block(site)
    assert "fastcgi_pass 127.0.0.1:9804;" in block
    assert "listen 8080;" in block
    assert "server_name a.local;" in block


def test_two_versions_two_ports(mgr, tmp_path):
    s1 = mgr.add("s1", "a.local", 8080, str(tmp_path / "w1"), "8.3.36")
    s2 = mgr.add("s2", "b.local", 8081, str(tmp_path / "w2"), "8.4.27")
    p1 = mgr.server_block(s1)
    p2 = mgr.server_block(s2)
    assert "9803" in p1 and "9804" in p2
    assert "9803" not in p2 and "9804" not in p1


def test_same_version_sites_share_port(mgr, tmp_path):
    s1 = mgr.add("s1", "a.local", 8080, str(tmp_path / "w1"), "8.3.36")
    s2 = mgr.add("s2", "b.local", 8081, str(tmp_path / "w2"), "8.3.36")
    assert "9803" in mgr.server_block(s1)
    assert "9803" in mgr.server_block(s2)


def test_write_nginx_conf_includes_each_site(mgr, tmp_path):
    mgr.add("s1", "a.local", 8080, str(tmp_path / "w1"), "8.3.36")
    mgr.add("s2", "b.local", 8081, str(tmp_path / "w2"), "8.4.27")
    text = mgr.write_nginx_conf().read_text(encoding="utf-8")
    assert mgr.conf_path("s1").as_posix() in text
    assert mgr.conf_path("s2").as_posix() in text


def test_next_port_skips_used(mgr, tmp_path):
    mgr.add("s1", "a.local", 8080, str(tmp_path / "w1"), "8.3.36")
    assert mgr.next_port() == 8081


def test_hand_written_conf_survives_regeneration(mgr, tmp_path):
    mgr.add("s1", "a.local", 8080, str(tmp_path / "w1"), "8.3.36")
    text = mgr.read_conf("s1").replace("index index.php index.html;", "index index.php;\n    # 手写注释")
    mgr.write_conf("s1", text)
    mgr.write_nginx_conf()  # 主配置重建不应覆盖片段
    assert "# 手写注释" in mgr.read_conf("s1")
