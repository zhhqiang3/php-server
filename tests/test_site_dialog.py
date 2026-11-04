"""站点弹窗：新增/编辑的校验与保存。"""

from __future__ import annotations

import pytest

pytest.importorskip("PyQt6")

from core.php_manager import PHPManager  # noqa: E402
from core.site_manager import SiteManager  # noqa: E402
from gui.site_dialog import SiteDialog  # noqa: E402


@pytest.fixture()
def sites(sandbox, fake_php):
    return SiteManager()


@pytest.fixture()
def hosts_file(tmp_path):
    """给 hosts 管理器一个临时文件，别动真的系统 hosts。"""
    p = tmp_path / "hosts"
    p.write_text("127.0.0.1 localhost\n", encoding="utf-8")
    from core.paths import save_config

    save_config({"hosts": {"path": str(p)}})
    return p


def test_new_dialog_defaults(qapp, sandbox, fake_php, sites):
    dlg = SiteDialog(None, sites, PHPManager())
    assert dlg.name.text() == ""
    assert dlg.name.isEnabled()
    assert dlg.port.value() == 80  # 默认端口 80
    assert dlg.php_box.count() == 2
    assert not dlg.use_ip.isChecked()


def test_new_dialog_host_follows_name(qapp, sandbox, fake_php, sites):
    dlg = SiteDialog(None, sites, PHPManager())
    assert dlg.host.text() == ""
    dlg.name.setText("mysite")
    assert dlg.host.text() == "mysite.local"


def test_new_dialog_port_skips_used(qapp, sandbox, fake_php, sites):
    sites.add("s1", "a.local", 80, str(sandbox / "w1"), "8.3.36")
    dlg = SiteDialog(None, sites, PHPManager())
    assert dlg.port.value() == 81


def test_use_ip_checkbox_fills_host(qapp, sandbox, fake_php, sites):
    dlg = SiteDialog(None, sites, PHPManager())
    dlg.name.setText("mysite")
    dlg.use_ip.setChecked(True)
    assert dlg.host.text() == "127.0.0.1"
    assert not dlg.host.isEnabled()
    dlg.use_ip.setChecked(False)
    assert dlg.host.text() == "mysite.local"
    assert dlg.host.isEnabled()


def test_local_domain_saved_to_hosts(qapp, sandbox, fake_php, sites, hosts_file):
    dlg = SiteDialog(None, sites, PHPManager())
    dlg.name.setText("mysite")
    dlg.root.setText(str(sandbox / "w1"))
    dlg._save()
    assert dlg.result_site is not None
    assert dlg.hosts_added is True
    assert "mysite.local" in hosts_file.read_text(encoding="utf-8")


def test_public_domain_not_written_to_hosts(qapp, sandbox, fake_php, sites, hosts_file):
    dlg = SiteDialog(None, sites, PHPManager())
    dlg.name.setText("mysite")
    dlg.host.setText("mysite.example.com")
    dlg.root.setText(str(sandbox / "w1"))
    dlg._save()
    assert dlg.result_site is not None
    assert dlg.hosts_added is False
    assert "mysite.example.com" not in hosts_file.read_text(encoding="utf-8")


def test_existing_host_not_written_again(qapp, sandbox, fake_php, sites, hosts_file):
    hosts_file.write_text("127.0.0.1\talready.local\n", encoding="utf-8")
    dlg = SiteDialog(None, sites, PHPManager())
    dlg.name.setText("already")
    dlg.root.setText(str(sandbox / "w1"))
    dlg._save()
    assert dlg.result_site is not None
    assert dlg.hosts_added is False
    assert hosts_file.read_text(encoding="utf-8").count("already.local") == 1


def test_edit_dialog_disables_name(qapp, sandbox, fake_php, sites):
    sites.add("s1", "a.local", 8080, str(sandbox / "w1"), "8.3.36")
    dlg = SiteDialog(None, sites, PHPManager(), edit_name="s1")
    assert dlg.name.text() == "s1"
    assert not dlg.name.isEnabled()
    assert dlg.host.text() == "a.local"
    assert dlg.port.value() == 8080
    assert dlg.php_box.currentText() == "8.3.36"


def test_save_creates_site(qapp, sandbox, fake_php, sites):
    dlg = SiteDialog(None, sites, PHPManager())
    dlg.name.setText("s1")
    dlg.host.setText("a.local")
    dlg.port.setValue(8080)
    dlg.root.setText(str(sandbox / "w1"))
    dlg._save()
    assert dlg.result_site is not None
    assert dlg.result_site["php"] == dlg.php_box.currentText()
    assert sites.get("s1") is not None


def test_save_duplicate_port_keeps_dialog_open(qapp, sandbox, fake_php, sites):
    sites.add("s1", "a.local", 8080, str(sandbox / "w1"), "8.3.36")
    dlg = SiteDialog(None, sites, PHPManager())
    dlg.name.setText("s2")
    dlg.port.setValue(8080)
    dlg.root.setText(str(sandbox / "w2"))
    dlg._save()
    assert dlg.result_site is None  # 保存失败，弹窗不关闭


def test_save_empty_name_rejected(qapp, sandbox, fake_php, sites):
    dlg = SiteDialog(None, sites, PHPManager())
    dlg.name.setText("   ")
    dlg._save()
    assert dlg.result_site is None


def test_edit_updates_version(qapp, sandbox, fake_php, sites):
    sites.add("s1", "a.local", 8080, str(sandbox / "w1"), "8.3.36")
    dlg = SiteDialog(None, sites, PHPManager(), edit_name="s1")
    idx = dlg.php_box.findText("8.4.27")
    assert idx >= 0
    dlg.php_box.setCurrentIndex(idx)
    dlg._save()
    assert sites.get("s1")["php"] == "8.4.27"
