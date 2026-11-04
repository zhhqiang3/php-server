"""PHP 页 GUI：版本列表、切换、扩展状态。"""

from __future__ import annotations

import pytest

pytest.importorskip("PyQt6")

from core.php_manager import PHPManager  # noqa: E402
from gui.php_page import PhpPage  # noqa: E402


@pytest.fixture()
def page(qapp, sandbox, fake_php):
    return PhpPage()


def test_installed_versions_listed(qapp, sandbox, fake_php, page):
    page.refresh()
    assert page.list.rowCount() == 2
    names = {page.list.item(r, 0).text() for r in range(page.list.rowCount())}
    assert names == {"8.3.36", "8.4.27"}


def test_active_label(qapp, sandbox, fake_php, page):
    page.refresh()
    assert "当前版本" in page.active.text()


def test_major_combo_populated(qapp, sandbox, fake_php, page):
    page.refresh()
    assert page.major.count() >= 1


def test_select_version_shows_extensions(qapp, sandbox, fake_php, page):
    page.refresh()
    page.list.selectRow(0)
    page._load_detail()
    assert page.detail_title.text().startswith("PHP ")
    assert page.ext_table.rowCount() > 0


def test_use_switches_active_version(qapp, sandbox, fake_php, page, stub_window):
    page.refresh()
    page.list.selectRow(0)
    version = page.list.item(0, 0).text()
    page.use()
    assert PHPManager().active() == version
    assert stub_window.statusBar().messages  # 状态栏提示


def test_extension_states_rendered(qapp, sandbox, fake_php, page):
    page.refresh()
    page.list.selectRow(0)
    page._load_detail()
    states = {
        page.ext_table.item(r, 0).text(): page.ext_table.item(r, 1).text()
        for r in range(page.ext_table.rowCount())
    }
    assert "curl" in states
    assert states["curl"] in ("已启用", "未启用")


def test_remove_site_version_removes(qapp, sandbox, fake_php, page):
    page.refresh()
    page.list.selectRow(0)
    version = page.list.item(0, 0).text()
    page.remove()
    assert version not in PHPManager().installed()
    assert page.list.rowCount() == 1
