"""日志文件定位与读取：Nginx 与 PHP。"""

from __future__ import annotations

from pathlib import Path

from core.paths import resolve
from core.php_manager import PHPManager
from core.site_manager import SiteManager

MAX_READ = 512 * 1024  # 单次最多读 512KB，日志太大时只取尾部


class LogFile:
    """一个可跟随刷新的日志文件。"""

    def __init__(self, label: str, path: Path) -> None:
        self.label = label
        self.path = path

    def exists(self) -> bool:
        return self.path.exists()

    def read(self, max_bytes: int = MAX_READ) -> str:
        """读尾部内容；不存在的文件返回提示文本。"""
        if not self.path.exists():
            return f"（文件不存在：{self.path}）"
        try:
            size = self.path.stat().st_size
            with self.path.open("rb") as f:
                if size > max_bytes:
                    f.seek(-max_bytes, 2)
                data = f.read()
            text = data.decode("utf-8", errors="replace")
            if size > max_bytes:
                # 扔掉半行
                nl = text.find("\n")
                if nl >= 0:
                    text = text[nl + 1:]
                text = f"……（文件 {size // 1024} KB，仅显示最后 {max_bytes // 1024} KB）\n" + text
            return text
        except OSError as exc:
            return f"（读取失败：{exc}）"


def nginx_logs() -> list[LogFile]:
    """Nginx 的 error/access，以及各站点的访问日志（如果片段里配了）。"""
    nginx_dir = resolve("data/nginx")
    logs = [
        LogFile("Nginx 错误日志", nginx_dir / "logs" / "error.log"),
        LogFile("Nginx 访问日志", nginx_dir / "logs" / "access.log"),
    ]
    try:
        sites = SiteManager()
        for site in sites.list_sites():
            # 站点片段若写了自己的 error_log/access_log，按 nginx 前缀解析相对路径
            text = sites.read_conf(site["name"])
            for directive in ("error_log", "access_log"):
                for line in text.splitlines():
                    s = line.strip()
                    if s.startswith(directive) and ";" in s:
                        value = s[len(directive):].split(";")[0].split()[0].strip()
                        if value in ("off", "syslog:") or not value:
                            continue
                        p = Path(value)
                        if not p.is_absolute():
                            p = nginx_dir / value
                        logs.append(LogFile(f"{site['name']} · {directive}", p))
    except Exception:  # noqa: BLE001 — 站点读取失败不影响基本日志
        pass
    # 去重（同一路径只显示一次）
    seen: set[Path] = set()
    unique = []
    for log in logs:
        key = log.path
        if key not in seen:
            seen.add(key)
            unique.append(log)
    return unique


def php_logs(version: str) -> list[LogFile]:
    """PHP 错误日志：php.ini 的 error_log 指令；没配则提示未开启。"""
    php = PHPManager()
    logs: list[LogFile] = []
    ini = php.ini_path(version)
    if ini is None:
        return logs
    from core.ini_editor import IniEditor

    target = IniEditor.parse_value(ini.read_text(encoding="utf-8", errors="replace"), "error_log")
    if target:
        p = Path(target)
        if not p.is_absolute():
            p = ini.parent / p
        logs.append(LogFile(f"PHP {version} 错误日志", p))
    return logs


def php_log_hint(version: str) -> str | None:
    """error_log 未配置时的提示。"""
    php = PHPManager()
    ini = php.ini_path(version)
    if ini is None:
        return None
    from core.ini_editor import IniEditor

    text = ini.read_text(encoding="utf-8", errors="replace")
    if not IniEditor.parse_value(text, "error_log"):
        return "php.ini 未设置 error_log，PHP 错误没有写到文件。可在「php.ini → 常用设置」之外的手工编辑里设置 error_log = php_errors.log"
    return None
