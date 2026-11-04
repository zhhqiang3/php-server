"""添加站点时写 nginx.conf + 创建 logs 目录（修复 logs 未定义）"""
from __future__ import annotations

import json
from pathlib import Path

from core.paths import load_config, resolve
from core.php_manager import PHPManager


class SiteManager:
    def __init__(self) -> None:
        cfg = load_config()
        nginx = cfg.get("nginx", {})
        self.sites_dir = resolve(nginx.get("sites_dir", "data/sites"))
        self.nginx_dir = resolve(nginx.get("dir", "data/nginx"))
        self.default_port = int(nginx.get("default_port", 8080))
        self.sites_dir.mkdir(parents=True, exist_ok=True)
        self.php = PHPManager()

    def list_sites(self) -> list[dict]:
        sites = []
        if not self.sites_dir.exists():
            return sites
        for p in sorted(self.sites_dir.iterdir()):
            meta = p / "site.json"
            if meta.exists():
                sites.append(json.loads(meta.read_text(encoding="utf-8")))
        return sites

    def add(self, name: str, host: str, port: int, root: str, php_version: str) -> dict:
        name = name.strip()
        if not name or any(c in name for c in r'\/:*?"<>|'):
            raise ValueError("站点名不合法")
        folder = self.sites_dir / name
        if folder.exists():
            raise FileExistsError(f"站点 {name} 已存在")
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
        (folder / "site.json").write_text(
            json.dumps(site, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        self.write_nginx_conf()
        return site

    def remove(self, name: str) -> None:
        folder = self.sites_dir / name
        if folder.exists():
            import shutil

            shutil.rmtree(folder)
        self.write_nginx_conf()

    def server_block(self, site: dict) -> str:
        root = Path(site["root"]).as_posix()
        host = site["host"]
        port = site["port"]
        php = site.get("php") or self.php.active() or "php"
        cgi_port = 9000 + (int(port) % 1000)
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
        conf_dir = self.nginx_dir / "conf"
        conf_dir.mkdir(parents=True, exist_ok=True)
        blocks = "\n".join(self.server_block(s) for s in self.list_sites())
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

	{blocks}
	}}
	"""
        path = conf_dir / "nginx.conf"
        path.write_text(text, encoding="utf-8")
        logs = self.nginx_dir / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        return path

    def next_port(self) -> int:
        used = {int(s["port"]) for s in self.list_sites()}
        port = self.default_port
        while port in used:
            port += 1
        return port
