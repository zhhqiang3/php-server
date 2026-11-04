"""php-cgi 进程：每个 PHP 版本一个 fastcgi 后端，按端口管理，换版本先停旧进程。"""

from __future__ import annotations

import subprocess
from pathlib import Path

from core.php_manager import PHPManager
from core.site_manager import SiteManager, cgi_port_for

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class CgiManager:
    """按监听端口管理 php-cgi：一个端口同时只允许一个进程。

    多版本 PHP 各占一个端口（端口由 PHPManager.cgi_port 统一分配），
    同版本的多个站点共用同一个 php-cgi 进程。
    站点改了 PHP 版本后再启动时，先把同端口旧版本进程停掉，再拉新版本，
    避免新旧进程抢占同一端口、请求仍打到旧版本。
    """

    def __init__(self) -> None:
        self.php = PHPManager()
        self.sites = SiteManager()
        # key 是监听端口，value 是 (版本目录名, Popen)
        self._procs: dict[int, tuple[str, subprocess.Popen]] = {}

    def alive(self, port: int) -> bool:
        entry = self._procs.get(port)
        return entry is not None and entry[1].poll() is None

    def start_site(self, site: dict) -> tuple[str, int]:
        version = site.get("php") or self.php.active()
        if not version:
            raise RuntimeError(f"站点 {site['name']} 没有指定 PHP 版本")
        cgi = self.php.cgi_exe(version)
        if cgi is None:
            raise FileNotFoundError(f"未找到 PHP {version} 的 php-cgi.exe")
        return cgi.parent.name, self.start(cgi.parent.name, cgi_port_for(site, self.php), cgi)

    def start(self, version: str, port: int, exe: Path | None = None) -> int:
        exe = exe or self.php.cgi_exe(version)
        if exe is None:
            raise FileNotFoundError(f"未找到 PHP {version} 的 php-cgi.exe")
        entry = self._procs.get(port)
        if entry is not None and entry[1].poll() is None:
            if entry[0] == version:
                return port  # 同版本同端口，直接复用
            self.stop(port)  # 换了版本：先停旧进程，避免它继续占着端口
        proc = subprocess.Popen(
            [str(exe), "-b", f"127.0.0.1:{port}"],
            cwd=str(exe.parent),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW,
        )
        self._procs[port] = (version, proc)
        return port

    def stop(self, port: int) -> None:
        entry = self._procs.pop(port, None)
        if entry is None or entry[1].poll() is not None:
            return
        proc = entry[1]
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    def stop_all(self) -> None:
        for port in list(self._procs):
            self.stop(port)

    def sync_all(self) -> list[tuple[str, int]]:
        """按当前站点配置对齐 php-cgi 进程。

        需要的端口启动，站点改过 PHP 版本后旧端口上的进程会被停掉，
        多余的进程也会回收。返回 [(版本, 端口)]。
        """
        wanted: dict[int, tuple[str, Path]] = {}
        for site in self.sites.list_sites():
            version = site.get("php") or self.php.active()
            if not version:
                continue
            cgi = self.php.cgi_exe(version)
            if cgi is None:
                continue
            wanted[cgi_port_for(site, self.php)] = (cgi.parent.name, cgi)
        # 站点不再需要的端口：停掉
        for port in list(self._procs):
            if port not in wanted:
                self.stop(port)
        started: list[tuple[str, int]] = []
        for port, (version, cgi) in wanted.items():
            self.start(version, port, cgi)
            started.append((version, port))
        return started

    def restart_all(self) -> list[tuple[str, int]]:
        """全部停掉再按当前站点配置重新拉起，返回 [(版本, 端口)]。"""
        self.stop_all()
        started: list[tuple[str, int]] = []
        for site in self.sites.list_sites():
            started.append(self.start_site(site))
        return started

    def running_ports(self) -> list[tuple[str, int]]:
        return [(v, p) for p, (v, proc) in self._procs.items() if proc.poll() is None]

    def cleanup_stale(self) -> list[int]:
        """杀掉上次会话遗留的 php-cgi（exe 在本工具 versions_dir 下、未被当前跟踪）。

        GUI 重启后 _procs 丢失，之前拉起的进程就成了"孤儿"，会重复占端口、
        还可能停不掉。返回被杀掉的 pid 列表。
        """
        tracked = {proc.pid for _, proc in self._procs.values() if proc.poll() is None}
        versions_root = str(self.php.versions_dir.resolve()).lower()
        killed: list[int] = []
        for pid, cmdline in _list_php_cgi():
            if pid in tracked:
                continue
            if versions_root not in cmdline.lower():
                continue  # 不是本工具装的 PHP，不动它
            try:
                subprocess.run(
                    ["taskkill", "/PID", str(pid), "/F"],
                    capture_output=True,
                    timeout=10,
                    creationflags=CREATE_NO_WINDOW,
                )
                killed.append(pid)
            except (OSError, subprocess.TimeoutExpired):
                continue
        return killed


def _list_php_cgi() -> list[tuple[int, str]]:
    """枚举系统里的 php-cgi.exe，返回 (pid, 命令行)。查询失败返回空。"""
    try:
        out = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-CimInstance Win32_Process -Filter \"Name='php-cgi.exe'\" "
                "| ForEach-Object { \"$($_.ProcessId)|$($_.CommandLine)\" }",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            creationflags=CREATE_NO_WINDOW,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    result: list[tuple[int, str]] = []
    for line in out.stdout.splitlines():
        pid, sep, cmdline = line.partition("|")
        if sep and pid.strip().isdigit():
            result.append((int(pid), cmdline))
    return result
