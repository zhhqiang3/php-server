"""首页：各模块卡片概览 + 快捷操作，点卡片跳到对应页签。"""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QVBoxLayout, QWidget

from core.log_manager import nginx_logs, php_logs
from gui.ui import Card, PageHeader, primary, restyle


class HomePage(QWidget):
    # 点卡片请求跳转，携带目标页 widget；主窗口负责切页签
    navigate = pyqtSignal(object)

    def __init__(self, site_page, php_page, nginx_page, hosts_page, log_page) -> None:
        super().__init__()
        self.site_page = site_page
        self.php_page = php_page
        self.nginx_page = nginx_page
        self.hosts_page = hosts_page
        self.log_page = log_page

        self.header = PageHeader("首页", "各模块状态总览，点卡片进入对应页面")

        self.site_card = self._make_card("站点", site_page)
        self.php_card = self._make_card("PHP", php_page)
        self.nginx_card = self._make_card("Nginx", nginx_page)
        self.hosts_card = self._make_card("Hosts", hosts_page)
        self.log_card = self._make_card("日志", log_page)

        # 站点卡：新增站点 / 重载配置
        self.add_site_btn = primary("新增站点…")
        self.add_site_btn.clicked.connect(self._add_site)
        self.site_card.add_action(self.add_site_btn)
        reload_btn = primary("重载配置")
        reload_btn.clicked.connect(self._reload)
        self.site_card.add_action(reload_btn)

        # Nginx 卡：启动/停止共用一个按钮，按状态切换
        self.nginx_toggle = primary("启动")
        self.nginx_toggle.clicked.connect(self._toggle_nginx)
        self.nginx_card.add_action(self.nginx_toggle)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)
        layout.addWidget(self.header)
        layout.addWidget(self.site_card)
        layout.addWidget(self.php_card)
        layout.addWidget(self.nginx_card)
        layout.addWidget(self.hosts_card)
        layout.addWidget(self.log_card)
        layout.addStretch(1)

        self.refresh()

    # ---------- 卡片 ----------

    def _make_card(self, title: str, target: QWidget) -> Card:
        card = Card(title)
        card.clicked.connect(lambda: self.navigate.emit(target))
        return card

    # ---------- 快捷操作 ----------

    def _add_site(self) -> None:
        self.site_page.add()
        self.refresh()

    def _reload(self) -> None:
        self.site_page.reload()
        self.refresh()

    def _toggle_nginx(self) -> None:
        self.site_page.toggle_nginx()
        self.refresh()

    # ---------- 刷新 ----------

    def refresh(self) -> None:
        # 站点：数量 + Nginx/php-cgi 状态
        running = self.site_page.nginx.running()
        try:
            n_cgi = len(self.site_page.cgi.running_ports())
        except Exception:  # noqa: BLE001 — 状态读不到时按 0 显示
            n_cgi = 0
        self.site_card.body.setText(
            f"{len(self.site_page.sites.list_sites())} 个站点"
            f" · Nginx {'运行中' if running else '未运行'}"
            f" · php-cgi {n_cgi} 个"
        )

        # PHP：当前版本与已装数量
        mgr = self.php_page.mgr
        self.php_card.body.setText(
            f"当前版本 {mgr.active() or '未选择'} · 已安装 {len(mgr.installed())} 个"
        )

        # Nginx：未安装引导去 Nginx 页，已装显示版本与运行状态
        ngr = self.nginx_page.mgr
        if ngr.installed():
            nrunning = ngr.running()
            self.nginx_card.body.setText(
                f"Nginx {ngr.version() or '未知版本'}"
                f" · {'运行中' if nrunning else '未运行'}"
            )
            self.nginx_toggle.setVisible(True)
            self._sync_toggle_btn(nrunning)
        else:
            self.nginx_card.body.setText("未安装 —— 到 Nginx 页下载安装")
            self.nginx_toggle.setVisible(False)

        # Hosts：本工具管理段的记录数
        try:
            n_hosts = len(self.hosts_page.mgr.entries())
        except Exception:  # noqa: BLE001
            n_hosts = 0
        self.hosts_card.body.setText(f"{n_hosts} 条记录")

        # 日志：Nginx 日志 + 当前 PHP 版本的日志
        active = mgr.active()
        n_logs = len(nginx_logs()) + (len(php_logs(active)) if active else 0)
        self.log_card.body.setText(f"{n_logs} 个日志文件")

    def _sync_toggle_btn(self, running: bool) -> None:
        """按 Nginx 运行状态切换启停按钮文案与样式。"""
        self.nginx_toggle.setText("停止" if running else "启动")
        self.nginx_toggle.setProperty("role", "danger" if running else "primary")
        restyle(self.nginx_toggle)
