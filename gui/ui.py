"""共用 UI 组件：页面标题栏、面包屑返回、主次按钮。

设计原则：
- 每页统一用「标题 + 副标题 + 右侧操作」的标题栏，页面结构一致
- 从子页面返回用面包屑（左上角带箭头的链接），比一个普通按钮明显得多
- 按钮分三级：primary（主操作）/ default（次要）/ danger（破坏性）
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


def _accent(dark: bool) -> str:
    return "#3f92d9" if dark else "#2f6fb5"


def _accent_hover(dark: bool) -> str:
    return "#4f9fe2" if dark else "#3a7fc7"


def build_stylesheet(dark: bool) -> str:
    """全局样式表。深浅色各一份，切换主题时整体替换。"""
    accent = _accent(dark)
    accent_hover = _accent_hover(dark)
    danger = "#e06c6c" if dark else "#c0392b"
    muted = "#8b8b8b" if dark else "#7a7a7a"
    line = "#3c3c3c" if dark else "#dcdcdc"
    hover_bg = "rgba(63,146,217,0.16)" if dark else "rgba(47,111,181,0.10)"
    on_bg = "rgba(46,204,113,0.16)" if dark else "rgba(39,174,96,0.12)"
    on_border = "#2ecc71" if dark else "#27ae60"
    on_text = "#2ecc71" if dark else "#1e8449"
    on_hover = "rgba(46,204,113,0.26)" if dark else "rgba(39,174,96,0.22)"
    card_bg = "#2b2b2b" if dark else "#fafafa"
    card_title = "#f0f0f0" if dark else "#1c1c1c"

    return f"""
    QPushButton {{
        padding: 5px 14px;
        border-radius: 4px;
        border: 1px solid {line};
        background: transparent;
        min-height: 18px;
    }}
    QPushButton:hover {{
        border-color: {accent};
        color: {accent};
    }}
    QPushButton:pressed {{
        background: {hover_bg};
    }}
    QPushButton:disabled {{
        color: {muted};
        border-color: {line};
    }}

    QPushButton[role="primary"] {{
        background: {accent};
        border: 1px solid {accent};
        color: #ffffff;
        font-weight: 600;
    }}
    QPushButton[role="primary"]:hover {{
        background: {accent_hover};
        border-color: {accent_hover};
        color: #ffffff;
    }}
    QPushButton[role="primary"]:disabled {{
        background: transparent;
        border-color: {line};
        color: {muted};
    }}

    QPushButton[role="danger"] {{
        color: {danger};
        border-color: transparent;
    }}
    QPushButton[role="danger"]:hover {{
        border-color: {danger};
        color: {danger};
        background: transparent;
    }}

    QPushButton[role="ghost"] {{
        border: 1px solid transparent;
        padding: 3px 8px;
        color: {accent};
        text-align: left;
    }}
    QPushButton[role="ghost"]:hover {{
        background: {hover_bg};
        border-color: transparent;
        color: {accent};
    }}

    QPushButton[state="on"] {{
        background: {on_bg};
        border: 1px solid {on_border};
        color: {on_text};
        font-weight: 600;
    }}
    QPushButton[state="on"]:hover {{
        background: {on_hover};
        border-color: {on_border};
        color: {on_text};
    }}
    QPushButton[state="off"] {{
        background: transparent;
        border: 1px solid {line};
        color: {muted};
    }}
    QPushButton[state="off"]:hover {{
        border-color: {muted};
        color: {muted};
    }}

    QFrame[card="true"] {{
        background: {card_bg};
        border: 1px solid {line};
        border-radius: 8px;
    }}
    QFrame[card="true"]:hover {{
        border-color: {accent};
    }}
    QLabel#cardTitle {{
        font-size: 12pt;
        font-weight: 600;
        color: {card_title};
        background: transparent;
        border: none;
    }}
    QLabel#cardBody {{
        color: {muted};
        background: transparent;
        border: none;
    }}

    QTabWidget::pane {{
        border: 1px solid {line};
        border-radius: 4px;
        top: -1px;
    }}
    QTabBar::tab {{
        padding: 6px 16px;
        border: 1px solid transparent;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
        margin-right: 2px;
    }}
    QTabBar::tab:selected {{
        border-color: {line};
        border-bottom-color: transparent;
        font-weight: 600;
    }}

    QGroupBox {{
        border: 1px solid {line};
        border-radius: 4px;
        margin-top: 10px;
        padding-top: 8px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 4px;
    }}

    QToolTip {{
        border: 1px solid {line};
        padding: 4px;
    }}
    """


def restyle(widget: QWidget) -> None:
    """改完 role 属性后重新套用样式（QSS 动态属性需要 unpolish/polish）。"""
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def primary(text: str, tooltip: str = "") -> QPushButton:
    btn = QPushButton(text)
    btn.setProperty("role", "primary")
    if tooltip:
        btn.setToolTip(tooltip)
    return btn


def danger(text: str, tooltip: str = "") -> QPushButton:
    btn = QPushButton(text)
    btn.setProperty("role", "danger")
    if tooltip:
        btn.setToolTip(tooltip)
    return btn


def ghost(text: str, tooltip: str = "") -> QPushButton:
    btn = QPushButton(text)
    btn.setProperty("role", "ghost")
    if tooltip:
        btn.setToolTip(tooltip)
    return btn


class Switch(QPushButton):
    """开关按钮：代替「状态文字 + 下拉框」的组合，避免同一个信息显示两遍。"""

    def __init__(self, text_on: str = "已启用", text_off: str = "未启用") -> None:
        super().__init__()
        self.text_on = text_on
        self.text_off = text_off
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedWidth(84)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.toggled.connect(lambda _on: self._restyle())
        self._restyle()

    def _restyle(self) -> None:
        on = self.isChecked()
        self.setText(self.text_on if on else self.text_off)
        self.setProperty("state", "on" if on else "off")
        restyle(self)

    def setChecked(self, checked: bool) -> None:  # noqa: N802 — Qt 命名
        super().setChecked(checked)
        self._restyle()


class Card(QFrame):
    """首页卡片：标题 + 信息行 + 右侧快捷操作，点卡片空白处导航到对应页。"""

    clicked = pyqtSignal()

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("card", True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("cardTitle")

        self.body = QLabel("")
        self.body.setObjectName("cardBody")
        self.body.setWordWrap(True)

        self.actions = QWidget()
        self.actions_layout = QHBoxLayout(self.actions)
        self.actions_layout.setContentsMargins(0, 0, 0, 0)
        self.actions_layout.setSpacing(8)

        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(12)
        title_row.addWidget(self.title_label)
        title_row.addWidget(self.actions, 0, Qt.AlignmentFlag.AlignTop)
        title_row.addStretch(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 12)
        layout.setSpacing(6)
        layout.addLayout(title_row)
        layout.addWidget(self.body)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 — Qt 命名
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)

    def add_action(self, btn: QPushButton) -> QPushButton:
        self.actions_layout.addWidget(btn)
        return btn


class PageHeader(QWidget):
    """统一的页面标题栏：可选面包屑 + 标题 + 副标题 + 右侧操作区。"""

    def __init__(
        self,
        title: str,
        subtitle: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("pageHeader")

        self.breadcrumb = QWidget()
        self.breadcrumb.setVisible(False)
        self.back_btn = ghost("← 返回")
        self.crumb_label = QLabel("")
        self.crumb_label.setStyleSheet("color: #888;")
        crumb_row = QHBoxLayout(self.breadcrumb)
        crumb_row.setContentsMargins(0, 0, 0, 0)
        crumb_row.setSpacing(8)
        crumb_row.addWidget(self.back_btn)
        crumb_row.addWidget(self.crumb_label)
        crumb_row.addStretch(1)

        self.title = QLabel(title)
        self.title.setObjectName("pageTitle")

        self.subtitle = QLabel(subtitle)
        self.subtitle.setObjectName("pageSubtitle")
        self.subtitle.setWordWrap(True)
        self.subtitle.setVisible(bool(subtitle))

        self.actions = QWidget()
        self.actions.setObjectName("pageActions")
        self.actions_layout = QHBoxLayout(self.actions)
        self.actions_layout.setContentsMargins(0, 0, 0, 0)
        self.actions_layout.setSpacing(8)

        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(12)
        title_row.addWidget(self.title)
        title_row.addWidget(self.subtitle, 1)
        title_row.addWidget(self.actions, 0, Qt.AlignmentFlag.AlignTop)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(self.breadcrumb)
        layout.addLayout(title_row)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setObjectName("headerLine")
        layout.addWidget(line)

    # ---------- 内容 ----------

    def set_subtitle(self, text: str) -> None:
        self.subtitle.setText(text)
        self.subtitle.setVisible(bool(text))

    def set_breadcrumb(self, parent_text: str, on_back) -> None:
        """显示面包屑：parent_text 是来源页名，点箭头返回。"""
        self.breadcrumb.setVisible(True)
        self.crumb_label.setText(parent_text)
        try:
            self.back_btn.clicked.disconnect()
        except TypeError:
            pass
        self.back_btn.clicked.connect(on_back)

    def add_action(self, widget: QWidget) -> QWidget:
        self.actions_layout.addWidget(widget)
        return widget

    def add_actions(self, widgets) -> None:
        for w in widgets:
            self.actions_layout.addWidget(w)

    def add_stretch(self) -> None:
        self.actions_layout.addStretch(1)


def header_style(dark: bool) -> str:
    """标题栏专用样式（配合全局样式表使用）。"""
    title_color = "#f0f0f0" if dark else "#1c1c1c"
    sub_color = "#909090" if dark else "#767676"
    line = "#3c3c3c" if dark else "#dcdcdc"
    return f"""
    QWidget#pageHeader {{ background: transparent; }}
    QLabel#pageTitle {{
        font-size: 16pt;
        font-weight: 600;
        color: {title_color};
    }}
    QLabel#pageSubtitle {{
        color: {sub_color};
        padding-top: 2px;
    }}
    QFrame#headerLine {{
        color: {line};
        background: {line};
        max-height: 1px;
        border: none;
    }}
    """
