"""PHP 多版本安装、切换、回退。"""

from __future__ import annotations

import re
import shutil
import zipfile
from pathlib import Path

import requests

from core.downloader import download
from core.paths import load_config, resolve, save_config

# windows.php.net 的 VS16 / VS17 NTS x64 包名随版本变化，这里只记录主版本到发行通道的映射。
# 实际文件名在安装时从 releases 页解析，避免写死过期补丁号。
RELEASES_URL = "https://windows.php.net/downloads/releases/"
ARCHIVE_URL = "https://windows.php.net/downloads/releases/archives/"

_ZIP_RE = re.compile(r"href=\"(php-(\d+\.\d+\.\d+)-(?:nts|ts)-Win32-[^\"]*?-(?:x64|nts-x64)\.zip)\"")


class PHPManager:
    def __init__(self) -> None:
        cfg = load_config()
        php_cfg = cfg.get("php", {})
        self.versions_dir = resolve(php_cfg.get("versions_dir", "data/versions"))
        self.versions_dir.mkdir(parents=True, exist_ok=True)
        self.majors: list[str] = list(php_cfg.get("majors", ["8.4", "8.3", "8.0", "7.4"]))
        self._cache: dict[str, str] = {}

    def installed(self) -> list[str]:
        """已解压的版本目录名，例如 8.3.14。"""
        if not self.versions_dir.exists():
            return []
        names = []
        for p in self.versions_dir.iterdir():
            if p.is_dir() and (p / "php.exe").exists():
                names.append(p.name)
        return sorted(names, key=_version_key, reverse=True)

    def active(self) -> str:
        return str(load_config().get("php", {}).get("active", "") or "")

    def php_exe(self, version: str) -> Path | None:
        """version 可以是完整版本 8.3.14，或主版本 8.3（取该主版本最新已装）。"""
        exact = self.versions_dir / version / "php.exe"
        if exact.exists():
            return exact
        matches = [v for v in self.installed() if v == version or v.startswith(version + ".")]
        if not matches:
            return None
        matches.sort(key=_version_key, reverse=True)
        return self.versions_dir / matches[0] / "php.exe"

    def cgi_exe(self, version: str) -> Path | None:
        exe = self.php_exe(version)
        if exe is None:
            return None
        cgi = exe.parent / "php-cgi.exe"
        return cgi if cgi.exists() else None

    def ini_path(self, version: str) -> Path | None:
        exe = self.php_exe(version)
        if exe is None:
            return None
        ini = exe.parent / "php.ini"
        if ini.exists():
            return ini
        for name in ("php.ini-development", "php.ini-production"):
            src = exe.parent / name
            if src.exists():
                shutil.copy(src, ini)
                return ini
        return None

    def use(self, version: str) -> str:
        exe = self.php_exe(version)
        if exe is None:
            raise FileNotFoundError(f"未安装 PHP {version}")
        full = exe.parent.name
        cfg = load_config()
        cfg.setdefault("php", {})["active"] = full
        save_config(cfg)
        return full

    # ---------- 下载安装 ----------

    def available(self, refresh: bool = True) -> dict[str, str]:
        """{完整版本号: 下载地址}，只含 NTS x64 包。"""
        if not refresh and self._cache:
            return dict(self._cache)
        found: dict[str, str] = {}
        for base in (RELEASES_URL, ARCHIVE_URL):
            try:
                text = requests.get(base, timeout=30).text
            except requests.RequestException:
                continue
            for name, version in _ZIP_RE.findall(text):
                if "nts" not in name.lower():
                    continue
                found.setdefault(version, base + name)
        self._cache = found
        return dict(found)

    def latest_per_major(self) -> dict[str, str]:
        """{主版本: 该主版本最新完整版本}。"""
        result: dict[str, str] = {}
        for version in self.available():
            major = ".".join(version.split(".")[:2])
            if major not in result or _version_key(version) > _version_key(result[major]):
                result[major] = version
        return result

    def install(self, version: str, url: str | None = None, progress=None, cancel=None) -> str:
        """下载指定完整版本并解压到 versions_dir。progress 见 core.downloader.download。"""
        dest = self.versions_dir / version
        if dest.exists() and (dest / "php.exe").exists():
            return version
        if url is None:
            url = self.available().get(version)
        if not url:
            raise FileNotFoundError(f"找不到 PHP {version} 的 NTS x64 下载地址")
        zip_path = self.versions_dir / f"php-{version}.zip"
        download(url, zip_path, progress=progress, cancel=cancel)
        try:
            dest.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(dest)
        finally:
            zip_path.unlink(missing_ok=True)
        self.ini_path(version)
        return version

    def install_latest(self, major: str, progress=None, cancel=None) -> str:
        """下载该主版本最新 NTS x64 zip 并解压。返回完整版本号。"""
        versions = [v for v in self.available() if v.startswith(major + ".")]
        if not versions:
            raise FileNotFoundError(f"windows.php.net 上找不到 PHP {major} 的 NTS x64 包")
        version = max(versions, key=_version_key)
        return self.install(version, progress=progress, cancel=cancel)

    def remove(self, version: str) -> None:
        dest = self.versions_dir / version
        if dest.exists():
            shutil.rmtree(dest)
        if self.active() == version:
            cfg = load_config()
            cfg.setdefault("php", {})["active"] = ""
            save_config(cfg)


def _version_key(name: str) -> tuple:
    raw = name
    if raw.startswith("php-"):
        raw = raw.split("-")[1]
    parts = []
    for piece in raw.split("."):
        digits = "".join(ch for ch in piece if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)
