"""php.ini 读取与安全写入（写入前备份）。"""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from core.php_manager import PHPManager


class IniEditor:
    def __init__(self) -> None:
        self.php = PHPManager()

    def path_for(self, version: str) -> Path:
        ini = self.php.ini_path(version)
        if ini is None:
            raise FileNotFoundError(f"找不到 PHP {version} 的 php.ini")
        return ini

    def read(self, version: str) -> str:
        return self.path_for(version).read_text(encoding="utf-8", errors="replace")

    def save(self, version: str, text: str) -> Path:
        ini = self.path_for(version)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = ini.with_name(f"php.ini.bak-{stamp}")
        shutil.copy2(ini, backup)
        ini.write_text(text, encoding="utf-8")  # 去掉 newline 参数        return backup

    def get_value(self, version: str, key: str) -> str | None:
        prefix = key.strip().lower()
        for line in self.read(version).splitlines():
            raw = line.strip()
            if not raw or raw.startswith(";") or raw.startswith("#") or "=" not in raw:
                continue
            k, _, v = raw.partition("=")
            if k.strip().lower() == prefix:
                return v.strip().strip('"')
        return None

    def set_value(self, version: str, key: str, value: str) -> bool:
        """改已有指令；找不到则追加到文件末尾。返回是否改到了已有行。"""
        lines = self.read(version).splitlines()
        found = False
        prefix = key.strip().lower()
        out = []
        for line in lines:
            raw = line.strip()
            if raw and not raw.startswith(";") and not raw.startswith("#") and "=" in raw:
                k, _, _v = raw.partition("=")
                if k.strip().lower() == prefix:
                    out.append(f"{key.strip()} = {value}")
                    found = True
                    continue
            out.append(line)
        if not found:
            out.append(f"{key.strip()} = {value}")
        self.save(version, "\n".join(out) + "\n")
        return found
