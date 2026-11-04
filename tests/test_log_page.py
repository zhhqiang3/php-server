"""日志页 GUI：扫描、读取、复制、清空。"""

from __future__ import annotations

import pytest

pytest.importorskip("PyQt6")

from core.log_manager import LogFile, nginx_logs, php_log_hint, php_logs  # noqa: E402
from gui.log_page import LogPage  # noqa: E402


@pytest.fixture()
def page(qapp, sandbox, fake_php):
    return LogPage()


def test_logfile_missing_file_message(tmp_path):
    lf = LogFile("x", tmp_path / "nope.log")
    assert "文件不存在" in lf.read()


def test_logfile_reads_tail(tmp_path):
    p = tmp_path / "a.log"
    p.write_text("line\n" * 100, encoding="utf-8")
    lf = LogFile("x", p)
    text = lf.read(max_bytes=100)
    assert "仅显示最后" in text
    assert text.strip().endswith("line")


def test_logfile_trims_partial_first_line(tmp_path):
    p = tmp_path / "a.log"
    p.write_text("x" * 50 + "\n完整行\n", encoding="utf-8")
    lf = LogFile("x", p)
    text = lf.read(max_bytes=60)
    assert text.splitlines()[-1] == "完整行"


def test_nginx_logs_always_has_error_and_access(sandbox):
    labels = [l.label for l in nginx_logs()]
    assert "Nginx 错误日志" in labels
    assert "Nginx 访问日志" in labels


def test_php_logs_empty_without_error_log(sandbox, fake_php):
    assert php_logs("8.3.36") == []
    assert php_log_hint("8.3.36")  # 没配 error_log 应有提示


def test_page_lists_logs(qapp, sandbox, fake_php, page):
    page.rescan()
    assert page.source.count() >= 2


def test_page_load_shows_content(qapp, sandbox, fake_php, page, tmp_path):
    err = tmp_path / "data" / "nginx" / "logs" / "error.log"
    err.parent.mkdir(parents=True, exist_ok=True)
    err.write_text("boom\n", encoding="utf-8")
    page.rescan()
    page.source.setCurrentIndex(0)
    page.load()
    assert "boom" in page.text.toPlainText()


def test_copy_all_uses_clipboard(qapp, sandbox, fake_php, page, tmp_path):
    err = tmp_path / "data" / "nginx" / "logs" / "error.log"
    err.parent.mkdir(parents=True, exist_ok=True)
    err.write_text("copyme\n", encoding="utf-8")
    page.rescan()
    page.source.setCurrentIndex(0)
    page.copy_all()
    from PyQt6.QtWidgets import QApplication

    assert "copyme" in QApplication.clipboard().text()
    assert "已复制" in page.hint.text()


def test_clear_log_empties_file(qapp, sandbox, fake_php, page, tmp_path):
    err = tmp_path / "data" / "nginx" / "logs" / "error.log"
    err.parent.mkdir(parents=True, exist_ok=True)
    err.write_text("boom\n", encoding="utf-8")
    page.rescan()
    page.source.setCurrentIndex(0)
    page.clear_log()
    assert err.stat().st_size == 0
