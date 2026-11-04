"""PHP 页：已装版本列表、下载安装、依赖/扩展查看。"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.ini_editor import EXTENSIONS, IniEditor
from core.php_manager import PHPManager
from gui.widgets import DownloadBar, DownloadTask


class PhpPage(QWidget):
    changed = pyqtSignal()
    view_ini_requested = pyqtSignal(str)  # 请求打开某个版本的 php.ini 配置

    def __init__(self) -> None:
        super().__init__()
        self.mgr = PHPManager()
        self.editor = IniEditor()
        self._modules_cache: dict[str, list[str]] = {}

        self.active = QLabel("当前版本：未选择")

        # --- 已安装 ---
        self.list = QTableWidget(0, 2)
        self.list.setHorizontalHeaderLabels(["版本", "php.ini"])
        self.list.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.list.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.list.currentCellChanged.connect(lambda *_: self._load_detail())
        self.list.doubleClicked.connect(self.view_ini_requested.emit)

        use_btn = QPushButton("设为当前版本")
        use_btn.clicked.connect(self.use)
        ini_btn = QPushButton("查看配置…")
        ini_btn.clicked.connect(self.view_ini)
        remove_btn = QPushButton("删除所选版本")
        remove_btn.clicked.connect(self.remove)
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.refresh)
        actions = QHBoxLayout()
        for b in (use_btn, ini_btn, remove_btn, refresh_btn):
            actions.addWidget(b)
        actions.addStretch(1)

        # --- 下载安装 ---
        self.major = QComboBox()
        note = QLabel("从 windows.php.net 下载 NTS x64 包，解压到 data/versions/")
        note.setStyleSheet("color: #888;")
        install_btn = QPushButton("安装该主版本最新版")
        install_btn.clicked.connect(self.install_latest)
        all_btn = QPushButton("查看可下载版本…")
        all_btn.clicked.connect(self.browse_available)
        self.download = DownloadBar()

        row = QHBoxLayout()
        row.addWidget(QLabel("主版本"))
        row.addWidget(self.major)
        row.addWidget(install_btn)
        row.addWidget(all_btn)
        row.addStretch(1)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self.active)
        left_layout.addWidget(self.list, 1)
        left_layout.addLayout(actions)
        left_layout.addWidget(note)
        left_layout.addLayout(row)
        left_layout.addWidget(self.download)

        # --- 详情 ---
        self.detail_title = QLabel("选择一个版本查看依赖与扩展")
        self.detail_title.setStyleSheet("font-weight: bold;")
        self.ext_table = QTableWidget(len(EXTENSIONS), 3)
        self.ext_table.setHorizontalHeaderLabels(["扩展", "状态", "说明"])
        self.ext_table.verticalHeader().setVisible(False)
        self.ext_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.ext_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.ext_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self.ext_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self.ext_table.horizontalHeader().setStretchLastSection(True)

        self.modules = QComboBox()
        self.modules_info = QLabel("运行时模块：选择版本后显示")
        self.modules_info.setWordWrap(True)
        self.modules_info.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        mods_row = QHBoxLayout()
        mods_row.addWidget(QLabel("运行时模块（php -m）"))
        mods_row.addWidget(self.modules, 1)
        mods_row.addWidget(self.modules_info, 3)

        self.ini_preview = QLabel("")
        self.ini_preview.setWordWrap(True)

        info_tab = QWidget()
        info_layout = QVBoxLayout(info_tab)
        info_layout.addWidget(self.ext_table, 1)
        info_layout.addLayout(mods_row)

        detail = QWidget()
        detail_layout = QVBoxLayout(detail)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_layout.addWidget(self.detail_title)
        detail_layout.addWidget(info_tab, 1)

        tabs = QTabWidget()
        tabs.addTab(left, "版本")
        tabs.addTab(detail, "依赖与扩展")

        layout = QVBoxLayout(self)
        layout.addWidget(tabs, 1)

        self.refresh()

    # ---------- 刷新 ----------

    def refresh(self) -> None:
        selected = self._selected()
        installed = self.mgr.installed()
        self.list.setRowCount(len(installed))
        for i, version in enumerate(installed):
            self.list.setItem(i, 0, QTableWidgetItem(version))
            ini = self.mgr.ini_path(version)
            self.list.setItem(i, 1, QTableWidgetItem(ini.name if ini else "—"))
        if selected in installed:
            self.list.selectRow(installed.index(selected))
        elif installed:
            self.list.selectRow(0)
        active = self.mgr.active() or "未选择"
        self.active.setText(f"当前版本：{active}")

        current = self.major.currentText()
        self.major.blockSignals(True)
        self.major.clear()
        self.major.addItems(self.mgr.majors)
        if current:
            idx = self.major.findText(current)
            if idx >= 0:
                self.major.setCurrentIndex(idx)
        self.major.blockSignals(False)
        self._load_detail()

    def _selected(self) -> str | None:
        row = self.list.currentRow()
        if row < 0:
            return None
        item = self.list.item(row, 0)
        return item.text() if item else None

    def _load_detail(self) -> None:
        version = self._selected()
        self.modules.clear()
        self.ext_table.setEnabled(version is not None)
        if not version:
            self.detail_title.setText("选择一个版本查看依赖与扩展")
            self.modules_info.setText("运行时模块：选择版本后显示")
            for row in range(self.ext_table.rowCount()):
                self.ext_table.setItem(row, 1, QTableWidgetItem("—"))
            return
        self.detail_title.setText(f"PHP {version}")

        enabled = self.editor.enabled_extensions(version)
        for row, ext in enumerate(EXTENSIONS):
            self.ext_table.setItem(row, 0, QTableWidgetItem(ext.name))
            self.ext_table.setItem(
                row, 1, QTableWidgetItem("已启用" if ext.name in enabled else "未启用")
            )
            self.ext_table.setItem(row, 2, QTableWidgetItem(ext.note))

        modules = self._modules_cache.get(version)
        if modules is None:
            modules = self.editor.runtime_modules(version) or []
            self._modules_cache[version] = modules
        if modules:
            self.modules.addItems(modules)
            self.modules_info.setText(f"{len(modules)} 个模块已加载（内置 + 已启用的扩展）")
            self.modules.setCurrentIndex(0)
        else:
            self.modules_info.setText("无法运行 php -m（文件缺失或执行失败）")

    # ---------- 操作 ----------

    def use(self) -> None:
        version = self._selected()
        if not version:
            return
        try:
            full = self.mgr.use(version)
        except Exception as exc:  # noqa: BLE001
            _err(self, "切换失败", exc)
            return
        self.refresh()
        self.changed.emit()
        self.window().statusBar().showMessage(f"当前 PHP 已切换为 {full}", 5000)

    def view_ini(self) -> None:
        """打开选中版本的 php.ini 配置页。"""
        version = self._selected()
        if not version:
            QMessageBox.information(self, "提示", "请先在列表中选择要查看配置的版本")
            return
        self.view_ini_requested.emit(version)

    def remove(self) -> None:
        version = self._selected()
        if not version:
            return
        if (
            QMessageBox.question(self, "删除", f"删除 PHP {version}？目录会被整个删除。")
            != QMessageBox.StandardButton.Yes
        ):
            return
        try:
            self.mgr.remove(version)
        except Exception as exc:  # noqa: BLE001
            _err(self, "删除失败", exc)
        self._modules_cache.pop(version, None)
        self.refresh()
        self.changed.emit()

    def install_latest(self) -> None:
        major = self.major.currentText()
        if not major:
            return
        self._start(DownloadTask(lambda progress, cancel: self.mgr.install_latest(
            major, progress=progress, cancel=cancel)), f"PHP {major} 最新版")

    def browse_available(self) -> None:
        try:
            available = self.mgr.available(refresh=True)
        except Exception as exc:  # noqa: BLE001
            _err(self, "获取版本列表失败", exc)
            return
        if not available:
            QMessageBox.warning(self, "提示", "没有解析到可下载的 NTS x64 版本")
            return
        installed = set(self.mgr.installed())
        items = [f"{v}  {'（已安装）' if v in installed else ''}" for v in _sorted_versions(available)]
        from PyQt6.QtWidgets import QInputDialog

        text, ok = QInputDialog.getItem(self, "可下载版本", "选择要安装的版本：", items, 0, False)
        if not ok or not text:
            return
        version = text.split()[0]
        if version in installed:
            QMessageBox.information(self, "提示", f"PHP {version} 已安装")
            return
        url = available[version]
        self._start(DownloadTask(lambda progress, cancel: self._install(version, url, progress, cancel)),
                    f"PHP {version}")

    def _install(self, version: str, url: str, progress, cancel) -> str:
        self.mgr.install(version, url=url, progress=progress, cancel=cancel)
        self.mgr.use(version)
        return version

    def _start(self, task: DownloadTask, label: str) -> None:
        if self.download.task is not None and self.download.task.isRunning():
            QMessageBox.information(self, "提示", "已有下载任务在进行")
            return
        task.done.connect(lambda version: self._finished(version))
        task.failed.connect(lambda msg: self._failed(msg))
        self.download.start(task)
        self.download.bar.setFormat(f"{label}：准备下载…")

    def _finished(self, version: str) -> None:
        self._modules_cache.pop(version, None)
        self.refresh()
        self.changed.emit()
        QMessageBox.information(self, "安装完成", f"已安装并切换到 PHP {version}")

    def _failed(self, msg: str) -> None:
        self.download.reset("失败")
        _err(self, "下载/安装失败", Exception(msg))


def _sorted_versions(available: dict[str, str]) -> list[str]:
    from core.php_manager import _version_key

    return sorted(available, key=_version_key, reverse=True)


def _err(parent, title: str, exc: Exception) -> None:
    QMessageBox.critical(parent, title, str(exc))
