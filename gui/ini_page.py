"""php.ini 页：常用设置（下拉/勾选）+ 原始文本编辑。"""

from __future__ import annotations

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


class _SettingRow:
    def __init__(self, setting: Setting) -> None:
        self.setting = setting
        self.box = QComboBox()
        self.box.setEditable(True)
        self.box.addItems(setting.values)
        self.box.setCurrentText("")
        self.box.setMinimumWidth(220)


class IniPage(QWidget):
    def __init__(self, php: PHPManager) -> None:
        super().__init__()
        self.php = php
        self.editor = IniEditor()
        self._rows: dict[str, _SettingRow] = {}

        self.version = QComboBox()
        self.version.setMinimumWidth(140)
        self.version.currentTextChanged.connect(self.refresh)
        reload_btn = QPushButton("重新读取")
        reload_btn.clicked.connect(self.refresh)

        top = QHBoxLayout()
        top.addWidget(QLabel("版本"))
        top.addWidget(self.version)
        top.addWidget(reload_btn)
        top.addStretch(1)

        tabs = QTabWidget()
        tabs.addTab(self._build_common_tab(), "常用设置")
        tabs.addTab(self._build_ext_tab(), "扩展")
        tabs.addTab(self._build_raw_tab(), "原始文本")

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(tabs, 1)

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
        form = QFormLayout()
        self._ext_boxes: dict[str, QComboBox] = {}
        for ext in EXTENSIONS:
            box = QComboBox()
            box.addItems(["未启用", "已启用"])
            box.setToolTip(ext.note or ext.dll)
            self._ext_boxes[ext.name] = box
            label = QLabel(ext.name + (f"（{ext.note}）" if ext.note else ""))
            form.addRow(label, box)

        save_btn = QPushButton("保存扩展开关")
        save_btn.clicked.connect(self.save_extensions)

        content = QWidget()
        content_layout = QVBoxLayout(content)
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
        save_btn = QPushButton("保存（自动备份）")
        save_btn.clicked.connect(self.save_raw)

        buttons = QHBoxLayout()
        buttons.addWidget(save_btn)
        buttons.addStretch(1)

        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.text, 1)
        layout.addLayout(buttons)
        return box

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
            row.box.blockSignals(False)
            idx = row.box.findText(value)
            if idx < 0 and value:
                row.box.addItem(value)
                row.box.setCurrentIndex(row.box.count() - 1)

        for name, box in self._ext_boxes.items():
            enabled = self.editor.extension_enabled(text, name)
            box.setCurrentIndex(1 if enabled else 0)

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
