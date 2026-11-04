"""PHP 多版本安装、切换、回退。"""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

import requests

from core.paths import load_config, resolve, save_config

# windows.php.net 的 VS16 / VS17 NTS x64 包名随版本变化，这里只记录主版本到发行通道的映射。
# 实际文件名在安装时从 releases 页解析，避免写死过期补丁号。
RELEASES_URL = "https://windows.php.net/downloads/releases/"
ARCHIVE_URL = "https://windows.php.net/downloads/releases/archives/"


class PHPManager:
    def __init__(self) -> None:
        cfg = load_config()
        php_cfg = cfg.get("php", {})
        self.versions_dir = resolve(php_cfg.get("versions_dir", "data/versions"))
        self.versions_dir.mkdir(parents=True, exist_ok=True)
        self.majors: list[str] = list(php_cfg.get("majors", ["8.4", "8.3", "8.0", "7.4"]))

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

    def install_latest(self, major: str, progress=None) -> str:
        """下载该主版本最新 NTS x64 zip 并解压。返回完整版本号。"""
        filename, url = self._find_latest_zip(major)
        version = _version_from_filename(filename)
        dest = self.versions_dir / version
        if dest.exists() and (dest / "php.exe").exists():
            return version
        zip_path = self.versions_dir / filename
        _download(url, zip_path, progress)
        dest.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(dest)
        zip_path.unlink(missing_ok=True)
        self.ini_path(version)
        return version

    def remove(self, version: str) -> None:
        dest = self.versions_dir / version
        if dest.exists():
            shutil.rmtree(dest)
        if self.active() == version:
            cfg = load_config()
            cfg.setdefault("php", {})["active"] = ""
            save_config(cfg)

    def _find_latest_zip(self, major: str) -> tuple[str, str]:
        """在 releases 页找 php-{major}.x-nts-Win32-*-x64.zip，找不到再查 archives。"""
        needle = f"php-{major}."
        for base in (RELEASES_URL, ARCHIVE_URL):
            text = requests.get(base, timeout=30).text
            candidates = []
            for part in text.split('"'):
                if part.startswith(needle) and "nts-Win32-" in part and part.endswith("-x64.zip"):
                    candidates.append(part)
            if candidates:
                candidates.sort(key=_version_key, reverse=True)
                name = candidates[0]
                return name, base + name
        raise FileNotFoundError(f"windows.php.net 上找不到 PHP {major} 的 NTS x64 包")


def _version_from_filename(name: str) -> str:
    # php-8.3.14-nts-Win32-vs16-x64.zip
    return name.split("-")[1]


def _version_key(name: str) -> tuple:
    raw = name
    if raw.startswith("php-"):
        raw = raw.split("-")[1]
    parts = []
    for piece in raw.split("."):
        digits = "".join(ch for ch in piece if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def _download(url: str, dest: Path, progress=None) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length") or 0)
        done = 0
        with dest.open("wb") as f:
            for chunk in r.iter_content(1024 * 64):
                if not chunk:
                    continue
                f.write(chunk)
                done += len(chunk)
                if progress and total:
                    progress(done, total)
