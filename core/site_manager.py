"""站点：每个站点的元数据与独立 nginx 配置片段。"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from core.paths import load_config, resolve
from core.php_manager import PHPManager

_SERVER_RE = re.compile(r"^\s*server\s*\{", re.MULTILINE)


class SiteManager:
    def __init__(self) -> None:
        cfg = load_config()
        nginx = cfg.get("nginx", {})
        self.sites_dir = resolve(nginx.get("sites_dir", "data/sites"))
        self.nginx_dir = resolve(nginx.get("dir", "data/nginx"))
        self.default_port = int(nginx.get("default_port", 8080))
        self.sites_dir.mkdir(parents=True, exist_ok=True)
        self.php = PHPManager()

    # ---------- 读取 ----------

    def list_sites(self) -> list[dict]:
        sites = []
        if not self.sites_dir.exists():
            return sites
        for p in sorted(self.sites_dir.iterdir()):
            meta = p / "site.json"
            if meta.exists():
                try:
                    sites.append(json.loads(meta.read_text(encoding="utf-8")))
                except (OSError, ValueError):
                    continue
        return sites

    def get(self, name: str) -> dict | None:
        return next((s for s in self.list_sites() if s["name"] == name), None)

    def conf_path(self, name: str) -> Path:
        return self.sites_dir / name / "site.conf"

    def read_conf(self, name: str) -> str:
        path = self.conf_path(name)
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8", errors="replace")

    def write_conf(self, name: str, text: str) -> Path:
        path = self.conf_path(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as f:
            f.write(text)
        return path

    # ---------- 增删改 ----------

    def add(self, name: str, host: str, port: int, root: str, php_version: str) -> dict:
        name = self._check_name(name)
        folder = self.sites_dir / name
        if folder.exists():
            raise FileExistsError(f"站点 {name} 已存在")
        self._check_port(port, exclude=name)
        root_path = Path(root).expanduser()
        root_path.mkdir(parents=True, exist_ok=True)
        index = root_path / "index.php"
        if not index.exists():
            index.write_text("<?php phpinfo(); ?>\n", encoding="utf-8")
        site = {
            "name": name,
            "host": host.strip() or "127.0.0.1",
            "port": int(port),
            "root": str(root_path),
            "php": php_version,
        }
        folder.mkdir(parents=True, exist_ok=True)
        self._save_meta(name, site)
        self.write_conf(name, self.server_block(site))
        self.write_nginx_conf()
        return site

    def update(
        self,
        name: str,
        host: str | None = None,
        port: int | None = None,
        root: str | None = None,
        php_version: str | None = None,
        regenerate: bool = False,
    ) -> dict:
        site = self.get(name)
        if site is None:
            raise FileNotFoundError(f"站点 {name} 不存在")
        if port is not None:
            self._check_port(port, exclude=name)
            site["port"] = int(port)
        if host is not None:
            site["host"] = host.strip() or "127.0.0.1"
        if root is not None:
            site["root"] = str(Path(root).expanduser())
        if php_version is not None:
            site["php"] = php_version
        self._save_meta(name, site)
        if regenerate:
            self.write_conf(name, self.server_block(site))
        self.write_nginx_conf()
        return site

    def remove(self, name: str) -> None:
        folder = self.sites_dir / name
        if folder.exists():
            shutil.rmtree(folder)
        self.write_nginx_conf()

    def _save_meta(self, name: str, site: dict) -> None:
        (self.sites_dir / name / "site.json").write_text(
            json.dumps(site, ensure_ascii=False, indent=2), encoding="utf-8"
        )


    @staticmethod
    def _check_name(name: str) -> str:
        name = name.strip()
        if not name or any(c in name for c in r'\/:*?"<>|'):
            raise ValueError("站点名不合法")
        return name

    def _check_port(self, port: int, exclude: str | None = None) -> None:
        for s in self.list_sites():
            if s.get("name") == exclude:
                continue
            if int(s.get("port", 0)) == int(port):
                raise ValueError(f"端口 {port} 已被站点 {s['name']} 使用")

    # ---------- 配置生成 ----------

    def server_block(self, site: dict) -> str:
        root = Path(site["root"]).as_posix()
        host = site["host"]
        port = site["port"]
        php = site.get("php") or self.php.active() or "php"
        cgi_port = cgi_port_for(site, self.php)
        return f"""server {{
    listen {port};
    server_name {host};
    root {root};
    index index.php index.html;

    location / {{
        try_files $uri $uri/ /index.php?$query_string;
    }}

    location ~ \\.php$ {{
        fastcgi_pass 127.0.0.1:{cgi_port};
        fastcgi_index index.php;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        include fastcgi_params;
        # php version: {php}
    }}
}}
"""

    def write_nginx_conf(self) -> Path:
        """主配置只包含各站点自己的 site.conf，手工改过的片段不会被覆盖。"""
        conf_dir = self.nginx_dir / "conf"
        conf_dir.mkdir(parents=True, exist_ok=True)
        includes = "\n".join(
            f"    include {self.conf_path(s['name']).as_posix()};"
            for s in self.list_sites()
            if self.conf_path(s["name"]).exists()
        )
        text = f"""worker_processes 1;
error_log logs/error.log;
pid logs/nginx.pid;

events {{
    worker_connections 256;
}}

http {{
    include mime.types;
    default_type application/octet-stream;
    sendfile on;
    access_log logs/access.log;

{includes}
}}
"""
        path = conf_dir / "nginx.conf"
        with path.open("w", encoding="utf-8", newline="") as f:
            f.write(text)
        (self.nginx_dir / "logs").mkdir(parents=True, exist_ok=True)
        return path

    def next_port(self) -> int:
        used = {int(s["port"]) for s in self.list_sites()}
        port = self.default_port
        while port in used:
            port += 1
        return port


def cgi_port_for_version(version: str, php: PHPManager | None = None) -> int:
    """PHP 版本对应的 fastcgi 端口。

    优先用 PHPManager 里登记的固定端口（多版本各占一个），登记失败时退回
    按版本号推算的端口。
    """
    php = php or PHPManager()
    try:
        return php.cgi_port(version)
    except Exception:  # noqa: BLE001 — 端口分配失败时用推算值兜底
        m = re.match(r"^(\d+)\.(\d+)", version.strip())
        if not m:
            return 9000
        return 9000 + int(m.group(1)) * 100 + int(m.group(2))


def cgi_port_for(site: dict, php: PHPManager | None = None) -> int:
    """站点的 php-cgi 端口：site.json 里显式记了 cgi_port 就用它，否则按 PHP 版本取。"""
    if site.get("cgi_port"):
        return int(site["cgi_port"])
    version = site.get("php") or (php or PHPManager()).active() or "8.0"
    return cgi_port_for_version(version, php)
