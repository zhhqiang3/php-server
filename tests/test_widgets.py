"""下载控件：进度条、取消按钮的信号接线。"""

from __future__ import annotations

import pytest

pytest.importorskip("PyQt6")

from gui.widgets import DownloadBar, DownloadTask  # noqa: E402


def test_download_task_emits_progress_and_done(qapp):
    got = []
    task = DownloadTask(lambda progress, cancel: "ok")
    task.done.connect(got.append)
    task.run()
    assert got == ["ok"]


def test_download_task_reports_failure(qapp):
    errors = []

    def boom(progress, cancel):
        raise RuntimeError("炸了")

    task = DownloadTask(boom)
    task.failed.connect(errors.append)
    task.run()
    assert errors == ["炸了"]


def test_cancel_button_calls_cancel(qapp):
    """点「取消」要真的把任务的取消标志置起来。"""
    task = DownloadTask(lambda progress, cancel: "ok")
    bar = DownloadBar()
    bar.start(task)
    bar.cancel_btn.click()
    assert task.is_cancelled() is True
    task.wait(2000)


def test_cancel_flag(qapp):
    task = DownloadTask(lambda progress, cancel: "ok")
    assert task.is_cancelled() is False
    task.cancel()
    assert task.is_cancelled() is True


def test_progress_updates_bar(qapp):
    bar = DownloadBar()
    bar.on_progress(50, 100, 1024 * 1024, 30)
    assert bar.bar.value() == 500
    assert "50.0%" in bar.bar.format()
    assert "MB/s" in bar.bar.format()


def test_progress_without_total(qapp):
    bar = DownloadBar()
    bar.on_progress(50, 0, 1024 * 1024, 0)
    assert bar.bar.maximum() == 0  # 不确定进度


def test_finished_sets_full(qapp):
    bar = DownloadBar()
    bar.on_finished()
    assert bar.bar.value() == bar.bar.maximum()
    assert bar.bar.format() == "完成"


def test_reset_clears(qapp):
    bar = DownloadBar()
    bar.reset("失败")
    assert bar.bar.value() == 0
    assert bar.bar.format() == "失败"
    assert bar.task is None


# ---------- 显隐：进度条只在下载时出现 ----------


def test_bar_hidden_by_default(qapp):
    bar = DownloadBar()
    assert bar.isHidden()


def test_start_shows_bar(qapp):
    task = DownloadTask(lambda progress, cancel: "ok")
    bar = DownloadBar()
    bar.start(task)
    assert not bar.isHidden()
    task.wait(2000)


def test_finished_hides_after_delay(qapp):
    bar = DownloadBar()
    bar.HIDE_DELAY_MS = 0
    bar.show()
    bar.on_finished()
    qapp.processEvents()
    assert bar.isHidden()


def test_reset_hides(qapp):
    bar = DownloadBar()
    bar.show()
    bar.reset("失败")
    assert bar.isHidden()
