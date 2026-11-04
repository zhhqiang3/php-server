"""Nginx 进程与安装：查找 nginx.exe、启动、停止、重载、从官网下载安装。"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import time
import zipfile
from pathlib import Path

import requests

from core.downloader import download
from core.paths import load_config, resolve, save_config
from core.site_manager import SiteManager

DOWNLOAD_PAGE = "https://nginx.org/en/download.html"
_VERSION_RE = re.compile(r'href="/download/nginx-(\d+\.\d+\.\d+)\.zip"')


class NginxManager:
    def __init__(self) -> None:
        self.sites = SiteManager()
        self.prefix = self.sites.nginx_dir

    def exe(self) -> Path | None:
        local = self.prefix / "nginx.exe"
        if local.exists():
            return local
        found = shutil.which("nginx")
        return Path(found) if found else None

    def installed(self) -> bool:
        return (self.prefix / "nginx.exe").exists()

    def version(self) -> str | None:
        """已安装 nginx 的版本号，未安装返回 None。"""
        exe = self.exe()
        if exe is None or exe.parent != self.prefix:
            return None
        try:
            out = subprocess.run(
                [str(exe), "-v"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
                cwd=str(self.prefix),
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except OSError:
            return None
        m = re.search(r"nginx/(\d+\.\d+\.\d+)", (out.stderr or "") + (out.stdout or ""))
        return m.group(1) if m else None

    def available(self) -> list[tuple[str, str]]:
        """官网 Windows 版列表 [(版本, 下载地址)]，新版本在前。"""
        text = requests.get(DOWNLOAD_PAGE, timeout=30).text
        seen: dict[str, str] = {}
        for version in _VERSION_RE.findall(text):
            seen.setdefault(version, f"https://nginx.org/download/nginx-{version}.zip")
        return sorted(seen.items(), key=lambda kv: _key(kv[0]), reverse=True)

    def install(self, version: str, url: str | None = None, progress=None, cancel=None) -> str:
        """下载官网 Windows 包并解压到 data/nginx（覆盖旧版本文件）。"""
        if self.running():
            raise RuntimeError("请先停止 Nginx 再安装")
        if url is None:
            url = f"https://nginx.org/download/nginx-{version}.zip"
        self.prefix.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="php-server-nginx-") as tmp:
            zip_path = Path(tmp) / f"nginx-{version}.zip"
            download(url, zip_path, progress=progress, cancel=cancel)
            with zipfile.ZipFile(zip_path) as zf:
                # 官方包内是一层 nginx-X.Y.Z/ 目录，去掉它
                top = f"nginx-{version}/"
                for member in zf.infolist():
                    name = member.filename.replace("\\", "/")
                    if not name.startswith(top):
                        continue
                    rel = name[len(top):]
                    if not rel:
                        continue
                    target = self.prefix / rel
                    if name.endswith("/"):
                        target.mkdir(parents=True, exist_ok=True)
                        continue
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(member) as src, target.open("wb") as dst:
                        shutil.copyfileobj(src, dst)
        cfg = load_config()
        cfg.setdefault("nginx", {})["version"] = version
        save_config(cfg)
        self.sites.write_nginx_conf()
        return version

    # ---------- 进程 ----------

    def running(self) -> bool:
        pid = self.prefix / "logs" / "nginx.pid"
        if not pid.exists():
            return False
        try:
            n = int(pid.read_text(encoding="utf-8", errors="replace").strip())
        except (ValueError, OSError):
            return False
        out = subprocess.run(
            ["tasklist", "/FI", f"PID eq {n}", "/NH"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return str(n) in (out.stdout or "")

    def start(self) -> None:
        exe = self.exe()
        if exe is None:
            raise FileNotFoundError(
                "未找到 nginx.exe。请在「Nginx」页从官网下载安装。"
            )
        if self.running():
            return
        self.sites.write_nginx_conf()
        # nginx 在 Windows 上主进程常驻前台，绝不能 subprocess.run 等它退出（会卡死 UI）。
        proc = subprocess.Popen(
            [str(exe), "-p", str(self.prefix), "-c", "conf/nginx.conf"],
            cwd=str(self.prefix),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                out, err = proc.communicate()
                text = ((err or "") + (out or "")).strip()
                raise RuntimeError(text or f"nginx 立即退出，退出码 {proc.returncode}")
            if self.running():
                return
            time.sleep(0.1)
        raise RuntimeError("nginx 启动超时：进程仍在运行但未写出 logs/nginx.pid，请查看 logs/error.log")

    def stop(self) -> None:
        exe = self.exe()
        if exe is None or not self.running():
            return
        result = self._run([str(exe), "-p", str(self.prefix), "-s", "stop"], check=False)
        if result.returncode != 0:
            raise RuntimeError(_nginx_error(result))

    def reload(self) -> None:
        exe = self.exe()
        if exe is None:
            raise FileNotFoundError("未找到 nginx.exe")
        self.sites.write_nginx_conf()
        if self.running():
            result = self._run([str(exe), "-p", str(self.prefix), "-s", "reload"], check=False)
            if result.returncode != 0:
                raise RuntimeError(_nginx_error(result))
        else:
            self.start()

    def test_config(self) -> str:
        exe = self.exe()
        if exe is None:
            raise FileNotFoundError("未找到 nginx.exe")
        self.sites.write_nginx_conf()
        result = self._run([str(exe), "-p", str(self.prefix), "-t"], check=False)
        if result.returncode != 0:
            raise RuntimeError(_nginx_error(result))
        return (result.stderr or result.stdout or "").strip()

    def _run(self, args: list[str], check: bool = True) -> subprocess.CompletedProcess:
        return subprocess.run(
            args,
            cwd=str(self.prefix),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )


def _nginx_error(result: subprocess.CompletedProcess) -> str:
    text = ((result.stderr or "") + (result.stdout or "")).strip()
    return text or f"nginx 退出码 {result.returncode}"


def _key(version: str) -> tuple:
    return tuple(int(p) for p in version.split("."))


def nginx_dir() -> Path:
    return resolve("data/nginx")
