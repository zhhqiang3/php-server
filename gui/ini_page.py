"""php.ini 页：常用设置 + 扩展（可搜索）+ 原始文本（可搜索）。"""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QColor, QTextCharFormat, QTextCursor
from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.ini_editor import COMMON_SETTINGS, EXTENSIONS, IniEditor, Setting
from core.php_manager import PHPManager

_ON_STYLE = "QLabel { color: #2ecc71; font-weight: bold; }"
_OFF_STYLE = "QLabel { color: #888; }"

_HIGHLIGHT = QTextCharFormat()
_HIGHLIGHT.setBackground(QColor(255, 200, 0, 90))
_HIGHLIGHT.setForeground(QColor(0, 0, 0))


class _SettingRow:
    def __init__(self, setting: Setting) -> None:
        self.setting = setting
        self.box = QComboBox()
        self.box.setEditable(True)
        self.box.addItems(setting.values)
        self.box.setCurrentText("")
        self.box.setMinimumWidth(220)


class _SearchBar(QWidget):
    """搜索框：回车/输入时触发回调，显示命中计数。"""

    def __init__(self, placeholder: str, on_search) -> None:
        super().__init__()
        self.on_search = on_search
        self.edit = QLineEdit()
        self.edit.setPlaceholderText(placeholder)
        self.edit.setClearButtonEnabled(True)
        self.edit.textChanged.connect(lambda _text: self._changed())
        self.edit.returnPressed.connect(lambda: self._changed(1))

        self.count = QLabel("")
        self.count.setStyleSheet("color: #888;")

        prev_btn = QPushButton("上一个")
        prev_btn.clicked.connect(lambda: self._changed(-1))
        next_btn = QPushButton("下一个")
        next_btn.clicked.connect(lambda: self._changed(1))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.edit, 1)
        layout.addWidget(self.count)
        layout.addWidget(prev_btn)
        layout.addWidget(next_btn)

    def _changed(self, nav=None) -> None:
        self.on_search(self.edit.text(), nav)


class IniPage(QWidget):
    """php.ini 配置页。默认不在主窗口里显示，由 PHP 列表的「查看配置」打开。"""

    closed = pyqtSignal()

    def __init__(self, php: PHPManager) -> None:
        super().__init__()
        self.php = php
        self.editor = IniEditor()
        self._rows: dict[str, _SettingRow] = {}
        self._ext_widgets: dict[str, tuple[QLabel, QLabel]] = {}  # name -> (状态标签, 行容器)

        self.version = QComboBox()
        self.version.setMinimumWidth(140)
        self.version.currentTextChanged.connect(self.refresh)
        reload_btn = QPushButton("重新读取")
        reload_btn.clicked.connect(self.refresh)
        back_btn = QPushButton("返回 PHP 列表")
        back_btn.clicked.connect(lambda: self.closed.emit())

        top = QHBoxLayout()
        top.addWidget(QLabel("版本"))
        top.addWidget(self.version)
        top.addWidget(reload_btn)
        top.addStretch(1)
        top.addWidget(back_btn)

        tabs = QTabWidget()
        tabs.addTab(self._build_common_tab(), "常用设置")
        tabs.addTab(self._build_ext_tab(), "扩展")
        tabs.addTab(self._build_raw_tab(), "原始文本")

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(tabs, 1)

    def show_version(self, version: str) -> None:
        """打开页面时定位到指定版本。"""
        self.refresh()
        idx = self.version.findText(version)
        if idx >= 0:
            self.version.setCurrentIndex(idx)
        else:
            self._reload()

    def _build_common_tab(self) -> QWidget:
        form = QFormLayout()
        for setting in COMMON_SETTINGS:
            row = _SettingRow(setting)
            self._rows[setting.key] = row
            wrap = QWidget()
            line = QHBoxLayout(wrap)
            line.setContentsMargins(0, 0, 0, 0)
            line.addWidget(row.box, 1)
            if setting.hint:
                hint = QLabel(setting.hint)
                hint.setStyleSheet("color: #888;")
                line.addWidget(hint, 1)
            form.addRow(setting.label, wrap)

        save_btn = QPushButton("保存常用设置")
        save_btn.clicked.connect(self.save_common)
        reset_btn = QPushButton("恢复为文件中的值")
        reset_btn.clicked.connect(self.refresh)

        buttons = QHBoxLayout()
        buttons.addWidget(save_btn)
        buttons.addWidget(reset_btn)
        buttons.addStretch(1)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.addLayout(form)
        content_layout.addLayout(buttons)
        content_layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        return scroll

    def _build_ext_tab(self) -> QWidget:
        self._ext_search = _SearchBar("筛选扩展（如 mysql、gd）…", self._filter_extensions)
        self._ext_boxes: dict[str, QComboBox] = {}

        form = QFormLayout()
        self._ext_rows: dict[str, QWidget] = {}
        for ext in EXTENSIONS:
            box = QComboBox()
            box.addItems(["未启用", "已启用"])
            box.setToolTip(ext.note or ext.dll)
            self._ext_boxes[ext.name] = box

            state = QLabel("未启用")
            state.setStyleSheet(_OFF_STYLE)
            state.setMinimumWidth(52)
            box.currentIndexChanged.connect(
                lambda _i, s=state: self._style_ext_state(s, _i)
            )

            name = QLabel(ext.name + (f"（{ext.note}）" if ext.note else ""))
            row = QWidget()
            line = QHBoxLayout(row)
            line.setContentsMargins(0, 0, 0, 0)
            line.addWidget(state)
            line.addWidget(box)
            self._ext_widgets[ext.name] = (state, row)
            self._ext_rows[ext.name] = row
            form.addRow(name, row)

        save_btn = QPushButton("保存扩展开关")
        save_btn.clicked.connect(self.save_extensions)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.addWidget(self._ext_search)
        content_layout.addLayout(form)
        content_layout.addWidget(save_btn)
        content_layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        return scroll

    def _build_raw_tab(self) -> QWidget:
        self.text = QTextEdit()
        self.text.setFontFamily("Consolas")
        self.text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.text.setPlaceholderText("完整 php.ini 内容（可直接编辑）")

        self._raw_search = _SearchBar("搜索（如 memory_limit）…", self._search_raw)

        save_btn = QPushButton("保存（自动备份）")
        save_btn.clicked.connect(self.save_raw)

        buttons = QHBoxLayout()
        buttons.addWidget(save_btn)
        buttons.addStretch(1)

        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._raw_search)
        layout.addWidget(self.text, 1)
        layout.addLayout(buttons)
        return box

    @staticmethod
    def _style_ext_state(label: QLabel, index: int) -> None:
        if index == 1:
            label.setText("● 已启用")
            label.setStyleSheet(_ON_STYLE)
        else:
            label.setText("未启用")
            label.setStyleSheet(_OFF_STYLE)

    def _filter_extensions(self, text: str, _nav=None) -> None:
        needle = text.strip().lower()
        shown = 0
        for name, row in self._ext_rows.items():
            match = not needle or needle in name.lower() or needle in (
                next(e.note for e in EXTENSIONS if e.name == name).lower()
            )
            row.setVisible(match)
            shown += 1 if match else 0
        self._ext_search.count.setText(f"{shown} 个")

    def _search_raw(self, text: str, nav=None) -> None:
        needle = text.strip()
        doc = self.text.document()
        # 清掉旧高亮
        cursor = QTextCursor(doc)
        cursor.select(QTextCursor.SelectionType.Document)
        fmt = QTextCharFormat()
        fmt.setBackground(self.text.palette().base())
        cursor.mergeCharFormat(fmt)

        if not needle:
            self._raw_search.count.setText("")
            return

        # 收集全部命中
        hits = []
        move = QTextCursor(doc)
        while True:
            move = doc.find(needle, move)
            if move.isNull():
                break
            hits.append(QTextCursor(move))
        self._raw_search.count.setText(f"{len(hits)} 处")

        if not hits:
            return
        for h in hits:
            h.mergeCharFormat(_HIGHLIGHT)
        # 导航：默认跳第一个，nav=1 下一个，nav=-1 上一个
        cur = self.text.textCursor().position()
        if nav == -1:
            before = [h for h in hits if h.selectionStart() < cur]
            target = before[-1] if before else hits[-1]
        else:
            after = [h for h in hits if h.selectionStart() > cur]
            target = after[0] if after else hits[0]
        self.text.setTextCursor(target)
        self.text.ensureCursorVisible()

    # ---------- 刷新 ----------

    def refresh(self) -> None:
        current = self.version.currentText()
        installed = self.php.installed()
        self.version.blockSignals(True)
        self.version.clear()
        self.version.addItems(installed)
        target = current if current in installed else (self.php.active() or "")
        if target in installed:
            self.version.setCurrentIndex(installed.index(target))
        self.version.blockSignals(False)
        self._reload()

    def _reload(self) -> None:
        version = self.version.currentText()
        if not version:
            self.text.clear()
            return
        try:
            text = self.editor.read(version)
        except Exception as exc:  # noqa: BLE001
            self.text.setPlainText(f"无法读取：{exc}")
            return
        self.text.setPlainText(text)

        for key, row in self._rows.items():
            value = IniEditor.parse_value(text, key) or ""
            row.box.blockSignals(True)
            row.box.setCurrentText(value)
            idx = row.box.findText(value)
            if idx < 0 and value:
                row.box.addItem(value)
                row.box.setCurrentIndex(row.box.count() - 1)
            row.box.blockSignals(False)

        for name, box in self._ext_boxes.items():
            enabled = self.editor.extension_enabled(text, name)
            state, _row = self._ext_widgets[name]
            box.blockSignals(True)
            box.setCurrentIndex(1 if enabled else 0)
            box.blockSignals(False)
            self._style_ext_state(state, box.currentIndex())

    # ---------- 保存 ----------

    def save_common(self) -> None:
        version = self.version.currentText()
        if not version:
            return
        changed = {}
        for key, row in self._rows.items():
            new = row.box.currentText().strip()
            if not new:
                continue
            old = self.editor.get_value(version, key)
            if (old or "") != new:
                changed[key] = new
        if not changed:
            QMessageBox.information(self, "提示", "没有改动")
            return
        try:
            self.editor.set_values(version, changed)
        except Exception as exc:  # noqa: BLE001
            _err(self, "保存失败", exc)
            return
        self._reload()
        QMessageBox.information(self, "已保存", "已写入 php.ini 并生成备份")

    def save_extensions(self) -> None:
        version = self.version.currentText()
        if not version:
            return
        enabled_now = self.editor.enabled_extensions(version)
        toggled: list[tuple[str, bool]] = []
        for name, box in self._ext_boxes.items():
            want = box.currentIndex() == 1
            if want != (name in enabled_now):
                toggled.append((name, want))
        if not toggled:
            QMessageBox.information(self, "提示", "没有改动")
            return
        try:
            for name, want in toggled:
                self.editor.set_extension(version, name, want)
        except Exception as exc:  # noqa: BLE001
            _err(self, "保存失败", exc)
            return
        self._reload()
        names = "、".join(f"{n}{'开' if w else '关'}" for n, w in toggled)
        QMessageBox.information(self, "已保存", f"{names}\n重启 php-cgi 后生效")

    def save_raw(self) -> None:
        version = self.version.currentText()
        if not version:
            return
        try:
            backup = self.editor.save(version, self.text.toPlainText())
        except Exception as exc:  # noqa: BLE001
            _err(self, "保存失败", exc)
            return
        self._reload()
        QMessageBox.information(self, "已保存", f"备份：{backup.name}")


def _err(parent, title: str, exc: Exception) -> None:
    QMessageBox.critical(parent, title, str(exc))
