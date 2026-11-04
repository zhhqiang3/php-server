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


def test_new_dialog_defaults(qapp, sandbox, fake_php, sites):
    dlg = SiteDialog(None, sites, PHPManager())
    assert dlg.name.text() == ""
    assert dlg.name.isEnabled()
    assert dlg.port.value() == sites.next_port()
    assert dlg.php_box.count() == 2


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
