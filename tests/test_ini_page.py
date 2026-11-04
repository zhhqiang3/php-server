"""php.ini 页 GUI：搜索筛选、扩展状态高亮、常用设置读写。"""

from __future__ import annotations

import pytest

pytest.importorskip("PyQt6")

from core.ini_editor import IniEditor  # noqa: E402
from core.php_manager import PHPManager  # noqa: E402
from gui.ini_page import IniPage  # noqa: E402


@pytest.fixture()
def page(qapp, sandbox, fake_php):
    return IniPage(PHPManager())


def test_version_combo_lists_installed(qapp, sandbox, fake_php, page):
    page.refresh()
    assert page.version.count() == 2
    items = {page.version.itemText(i) for i in range(page.version.count())}
    assert items == {"8.3.36", "8.4.27"}


def _select(page, version: str) -> None:
    page.version.setCurrentIndex(page.version.findText(version))


def test_common_settings_loaded(qapp, sandbox, fake_php, page):
    page.refresh()
    _select(page, "8.3.36")
    row = page._rows["memory_limit"]
    assert row.box.currentText() == "128M"


def test_save_common_writes_ini(qapp, sandbox, fake_php, page):
    page.refresh()
    _select(page, "8.3.36")
    page._rows["memory_limit"].box.setCurrentText("512M")
    page.save_common()
    editor = IniEditor()
    assert editor.get_value("8.3.36", "memory_limit") == "512M"
    assert editor.get_value("8.4.27", "memory_limit") == "128M"  # 另一个版本不受影响


def test_extension_filter_hides_rows(qapp, sandbox, fake_php, page):
    page.refresh()
    page._filter_extensions("curl", None)
    assert page._ext_rows["curl"].isVisibleTo(page) or not page._ext_rows["curl"].isHidden()
    hidden = [n for n, r in page._ext_rows.items() if r.isHidden()]
    assert "curl" not in hidden
    assert "gd" in hidden


def test_extension_filter_count(qapp, sandbox, fake_php, page):
    page.refresh()
    page._filter_extensions("curl", None)
    assert page._ext_search.count.text() == "1 个"


def test_extension_state_highlight(qapp, sandbox, fake_php, page):
    page.refresh()
    _select(page, "8.3.36")
    editor = IniEditor()
    editor.set_extension("8.3.36", "curl", True)
    page.refresh()
    state, _row = page._ext_widgets["curl"]
    assert "已启用" in state.text()
    assert "color" in state.styleSheet()

    off_state, _ = page._ext_widgets["gd"]
    assert "未启用" in off_state.text()


def test_raw_search_reports_hits(qapp, sandbox, fake_php, page):
    page.refresh()
    page._search_raw("memory_limit", None)
    assert "处" in page._raw_search.count.text()


def test_raw_search_navigates(qapp, sandbox, fake_php, page):
    page.refresh()
    page._search_raw("extension", None)
    count_before = page._raw_search.count.text()
    page._search_raw("extension", 1)
    assert page._raw_search.count.text() == count_before


def test_save_raw_writes_file(qapp, sandbox, fake_php, page):
    page.refresh()
    _select(page, "8.3.36")
    page.text.setPlainText("memory_limit = 777M\n")
    page.save_raw()
    assert IniEditor().get_value("8.3.36", "memory_limit") == "777M"
