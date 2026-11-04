"""系统 hosts 中由本工具管理的一段记录。"""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from core.paths import load_config

DEFAULT_HOSTS = Path(r"C:\Windows\System32\drivers\etc\hosts")


class HostsManager:
    def __init__(self) -> None:
        cfg = load_config().get("hosts", {})
        custom = str(cfg.get("path") or "").strip()
        self.path = Path(custom) if custom else DEFAULT_HOSTS
        self.begin = str(cfg.get("marker_begin", "# BEGIN php-server"))
        self.end = str(cfg.get("marker_end", "# END php-server"))

    def read(self) -> str:
        if not self.path.exists():
            return ""
        return self.path.read_text(encoding="utf-8", errors="replace")

    def entries(self) -> list[tuple[str, str]]:
        rows: list[tuple[str, str]] = []
        inside = False
        for line in self.read().splitlines():
            s = line.strip()
            if s == self.begin:
                inside = True
                continue
            if s == self.end:
                inside = False
                continue
            if not inside or not s or s.startswith("#"):
                continue
            parts = s.split()
            if len(parts) >= 2:
                rows.append((parts[0], parts[1]))
        return rows

    def add(self, ip: str, host: str) -> None:
        ip, host = ip.strip(), host.strip()
        if not ip or not host:
            raise ValueError("IP 和域名都不能为空")
        current = [(a, b) for a, b in self.entries() if b.lower() != host.lower()]
        current.append((ip, host))
        self._write_block(current)

    def remove(self, host: str) -> None:
        host = host.strip().lower()
        current = [(a, b) for a, b in self.entries() if b.lower() != host]
        self._write_block(current)

    def _write_block(self, rows: list[tuple[str, str]]) -> None:
        text = self.read()
        lines = text.splitlines()
        kept: list[str] = []
        inside = False
        for line in lines:
            s = line.strip()
            if s == self.begin:
                inside = True
                continue
            if s == self.end:
                inside = False
                continue
            if not inside:
                kept.append(line)
        while kept and not kept[-1].strip():
            kept.pop()
        block = [self.begin]
        for ip, host in rows:
            block.append(f"{ip}\t{host}")
        block.append(self.end)
        body = "\n".join(kept + [""] + block) + "\n"
        self._backup()
        self.path.write_text(body, encoding="utf-8")  # 去掉 newline 参数
    def _backup(self) -> None:
        if not self.path.exists():
            return
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        dest = self.path.with_name(self.path.name + f".bak-{stamp}")
        try:
            shutil.copy2(self.path, dest)
        except OSError:
            # 系统目录可能无权限写备份到同目录，忽略，写入本身仍会抛错
            pass
