"""信号接线审计：找出「信号 -> 另一个信号的 emit」这种危险接法。

PyQt 里 clicked(bool) 直连 pyqtSignal().emit 会把 bool 塞给无参信号，
运行时抛 TypeError；这类问题编译期查不出来，必须真跑一遍。
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap

import pytest

pytest.importorskip("PyQt6")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PRELUDE = f"""
import os, sys
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, {ROOT!r})
from PyQt6.QtWidgets import QApplication, QMessageBox
app = QApplication([])
for _n in ("information", "warning", "critical", "question"):
    setattr(QMessageBox, _n, staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok))
import core.nginx_manager as nm
nm.NginxManager.running = lambda self: False
nm.NginxManager.version = lambda self: None
nm.NginxManager.installed = lambda self: False
from gui.main import MainWindow
win = MainWindow()
win.show()
app.processEvents()
"""

CASES = {
    "点 php.ini 的「返回 PHP 列表」按钮": """
        win.show_ini("8.4.27")
        app.processEvents()
        btn = win.ini_page.findChildren(type(win.ini_page.version).__mro__[0].__bases__[0])
        # 直接找那个按钮：按文字匹配
        from PyQt6.QtWidgets import QPushButton
        target = [b for b in win.ini_page.findChildren(QPushButton)
                  if "返回" in b.text()]
        assert target, "找不到返回按钮"
        target[0].click()
        app.processEvents()
        assert win.tabs.currentIndex() == win._index_of(win.tabs, win.php_page), "应回到 PHP 页"
        print("OK")
    """,
    "双击 PHP 版本行": """
        page = win.php_page
        page.refresh()
        page.list.setCurrentCell(0, 0)
        page.list.doubleClicked.emit(page.list.model().index(0, 0))
        app.processEvents()
        assert win.tabs.currentIndex() == win._index_of(win.tabs, win.ini_page), "应切到 php.ini 页"
        print("OK")
    """,
    "双击站点行（弹窗打桩为取消）": """
        from gui.site_dialog import SiteDialog
        SiteDialog.exec = lambda self: SiteDialog.DialogCode.Rejected
        page = win.site_page
        page.refresh()
        page.table.setCurrentCell(0, 0)
        page.table.doubleClicked.emit(page.table.model().index(0, 0))
        app.processEvents()
        print("OK")
    """,
    "点 PHP「查看配置」按钮": """
        from PyQt6.QtWidgets import QPushButton
        page = win.php_page
        page.refresh()
        page.list.setCurrentCell(0, 0)
        btn = [b for b in page.findChildren(QPushButton) if "查看配置" in b.text()]
        assert btn, "找不到查看配置按钮"
        btn[0].click()
        app.processEvents()
        assert win.tabs.currentIndex() == win._index_of(win.tabs, win.ini_page)
        print("OK")
    """,
    "ini 搜索框输入触发回调": """
        win.show_ini("8.4.27")
        app.processEvents()
        bar = win.ini_page.findChildren(type(win.ini_page).__mro__[0])
        from gui.ini_page import _SearchBar
        bars = win.ini_page.findChildren(_SearchBar)
        assert bars, "找不到搜索框"
        bars[0].edit.setText("memory_limit")
        app.processEvents()
        assert "处" in bars[0].count.text(), bars[0].count.text()
        print("OK")
    """,
    "扩展下拉切换触发样式更新": """
        from PyQt6.QtWidgets import QComboBox
        win.show_ini("8.4.27")
        app.processEvents()
        boxes = win.ini_page._ext_boxes
        assert boxes, "没有扩展下拉"
        name, box = next(iter(boxes.items()))
        box.setCurrentIndex(1)
        app.processEvents()
        state = win.ini_page._ext_widgets[name][0]
        assert "已启用" in state.text(), state.text()
        print("OK")
    """,
}


@pytest.mark.parametrize("name", sorted(CASES))
def test_signal_wiring(name):
    """每个用例单独跑子进程：信号参数错配会让进程直接崩掉，不会污染其它用例。"""
    code = PRELUDE + textwrap.dedent(CASES[name])
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=90,
    )
    assert proc.returncode == 0, f"{name} 失败:\n{proc.stderr}\n{proc.stdout}"
    assert "OK" in proc.stdout
