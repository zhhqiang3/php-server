"""php.ini 读取 / 备份写入 / 常用指令设置 / 扩展开关。"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from core.php_manager import PHPManager


@dataclass(frozen=True)
class Setting:
    key: str
    label: str
    values: tuple[str, ...]
    hint: str = ""


# 常用设置：下拉框给常用值，也允许手填
COMMON_SETTINGS: tuple[Setting, ...] = (
    Setting("memory_limit", "内存上限", ("128M", "256M", "512M", "1024M", "-1"),
            "脚本可用内存，-1 表示不限制"),
    Setting("upload_max_filesize", "上传文件上限", ("2M", "8M", "32M", "64M", "128M"),
            "单个上传文件的大小"),
    Setting("post_max_size", "POST 体积上限", ("8M", "16M", "32M", "64M", "128M"),
            "需不小于 upload_max_filesize"),
    Setting("max_execution_time", "最长执行时间", ("30", "60", "120", "300", "0"),
            "秒，0 表示不限制"),
    Setting("max_input_vars", "最大输入变量数", ("1000", "3000", "5000", "10000"), ""),
    Setting("date.timezone", "时区", ("Asia/Shanghai", "PRC", "UTC"), ""),
    Setting("display_errors", "显示错误", ("On", "Off"), "开发建议 On，对外服务建议 Off"),
    Setting("error_reporting", "错误级别", ("E_ALL", "E_ALL & ~E_DEPRECATED & ~E_STRICT", "E_ALL & ~E_NOTICE"),
            ""),
    Setting("log_errors", "记录错误日志", ("On", "Off"), ""),
    Setting("default_charset", "默认字符集", ("UTF-8", "GBK"), ""),
    Setting("short_open_tag", "短标签 <?", ("Off", "On"), ""),
    Setting("expose_php", "暴露 PHP 版本", ("Off", "On"), "响应头里的 X-Powered-By"),
    Setting("output_buffering", "输出缓冲", ("4096", "Off"), ""),
    Setting("file_uploads", "允许上传文件", ("On", "Off"), ""),
    Setting("allow_url_fopen", "允许 url fopen", ("On", "Off"), ""),
    Setting("cgi.fix_pathinfo", "cgi.fix_pathinfo", ("1", "0"), ""),
    Setting("opcache.enable", "OPcache", ("1", "0"), ""),
)


@dataclass(frozen=True)
class PhpExtension:
    name: str          # php_xxx.dll 对应的扩展名，例如 mbstring
    dll: str           # 文件名
    note: str = ""


# Windows 版 PHP 自带的常用扩展
EXTENSIONS: tuple[PhpExtension, ...] = (
    PhpExtension("bcmath", "php_bcmath.dll"),
    PhpExtension("bz2", "php_bz2.dll"),
    PhpExtension("calendar", "php_calendar.dll"),
    PhpExtension("curl", "php_curl.dll"),
    PhpExtension("exif", "php_exif.dll", "依赖 mbstring"),
    PhpExtension("ffi", "php_ffi.dll"),
    PhpExtension("fileinfo", "php_fileinfo.dll"),
    PhpExtension("ftp", "php_ftp.dll"),
    PhpExtension("gd", "php_gd.dll"),
    PhpExtension("gettext", "php_gettext.dll"),
    PhpExtension("gmp", "php_gmp.dll"),
    PhpExtension("imap", "php_imap.dll"),
    PhpExtension("intl", "php_intl.dll"),
    PhpExtension("ldap", "php_ldap.dll"),
    PhpExtension("mbstring", "php_mbstring.dll"),
    PhpExtension("mysqli", "php_mysqli.dll", "依赖 mysqlnd"),
    PhpExtension("openssl", "php_openssl.dll"),
    PhpExtension("pdo_mysql", "php_pdo_mysql.dll"),
    PhpExtension("pdo_pgsql", "php_pdo_pgsql.dll"),
    PhpExtension("pdo_sqlite", "php_pdo_sqlite.dll"),
    PhpExtension("pgsql", "php_pgsql.dll"),
    PhpExtension("shmop", "php_shmop.dll"),
    PhpExtension("snmp", "php_snmp.dll"),
    PhpExtension("soap", "php_soap.dll"),
    PhpExtension("sockets", "php_sockets.dll"),
    PhpExtension("sodium", "php_sodium.dll"),
    PhpExtension("sqlite3", "php_sqlite3.dll"),
    PhpExtension("tidy", "php_tidy.dll"),
    PhpExtension("xsl", "php_xsl.dll"),
    PhpExtension("zip", "php_zip.dll"),
)

_INI_KEY_RE = re.compile(r"^\s*([A-Za-z_][\w.]*)\s*=")
_EXT_RE = re.compile(r"^\s*;?\s*extension\s*=\s*\"?([\w]+)\"?", re.IGNORECASE)


class IniEditor:
    def __init__(self) -> None:
        self.php = PHPManager()

    # ---------- 路径与读写 ----------

    def path_for(self, version: str) -> Path:
        ini = self.php.ini_path(version)
        if ini is None:
            raise FileNotFoundError(f"找不到 PHP {version} 的 php.ini")
        return ini

    def read(self, version: str) -> str:
        return self.path_for(version).read_text(encoding="utf-8", errors="replace")

    def save(self, version: str, text: str) -> Path:
        """写入并返回备份文件路径；首次改动时若 php.ini 不存在则先生成。"""
        ini = self.path_for(version)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = ini.with_name(f"php.ini.bak-{stamp}")
        shutil.copy2(ini, backup)
        with ini.open("w", encoding="utf-8", newline="") as f:
            f.write(text)
        return backup

    # ---------- 单值读写 ----------

    @staticmethod
    def parse_value(text: str, key: str) -> str | None:
        prefix = key.strip().lower()
        for line in text.splitlines():
            raw = line.strip()
            if not raw or raw.startswith(";") or raw.startswith("#") or "=" not in raw:
                continue
            k, _, v = raw.partition("=")
            if k.strip().lower() == prefix:
                return v.strip().strip('"')
        return None

    def get_value(self, version: str, key: str) -> str | None:
        return self.parse_value(self.read(version), key)

    def set_value(self, version: str, key: str, value: str) -> bool:
        """改已有指令；找不到则追加到文件末尾。返回是否改到了已有行。"""
        lines = self.read(version).splitlines()
        existed = key.strip().lower() in _assigned_keys(lines)
        self.save(version, "\n".join(_set_line(lines, key, value)) + "\n")
        return existed

    def set_values(self, version: str, pairs: dict[str, str]) -> None:
        lines = self.read(version).splitlines()
        for k, v in pairs.items():
            lines = _set_line(lines, k, v)
        self.save(version, "\n".join(lines) + "\n")

    def _update(self, version: str, fn) -> None:
        lines = self.read(version).splitlines()
        self.save(version, "\n".join(fn(lines)) + "\n")

    # ---------- 扩展 ----------

    def extension_enabled(self, text: str, name: str) -> bool:
        for line in text.splitlines():
            s = line.strip()
            if not s or s.startswith(";") or s.startswith("#"):
                continue
            m = _EXT_RE.match(s)
            if m and m.group(1).lower() == name.lower():
                return True
        return False

    def enabled_extensions(self, version: str) -> set[str]:
        return {e.name for e in EXTENSIONS if self.extension_enabled(self.read(version), e.name)}

    def set_extension(self, version: str, name: str, enabled: bool) -> None:
        ext = next((e for e in EXTENSIONS if e.name.lower() == name.lower()), None)
        if ext is None:
            raise ValueError(f"未知扩展：{name}")

        def apply(lines: list[str]) -> list[str]:
            ext_dir_ok = any(
                (_INI_KEY_RE.match(s) and _INI_KEY_RE.match(s).group(1).lower() == "extension_dir")
                for s in lines
            )
            out: list[str] = []
            done = False
            for line in lines:
                s = line.strip()
                m = None if s.startswith(";") or s.startswith("#") else _EXT_RE.match(s)
                if m is None and s.startswith(";"):
                    m = _EXT_RE.match(s)  # 被注释掉的 extension= 行
                if m and m.group(1).lower() == ext.name.lower():
                    if enabled:
                        out.append(f"extension={ext.name}")
                    else:
                        out.append(f";extension={ext.name}")
                    done = True
                    continue
                out.append(line)
            if enabled and not done:
                out.append(f"extension={ext.name}")
            if enabled and not ext_dir_ok:
                # 没有 extension_dir 时用相对 ext 目录，PHP 会按 php.exe 所在目录解析
                out.insert(0, 'extension_dir = "ext"')
            return out

        self._update(version, apply)

    # ---------- 运行时信息 ----------

    def runtime_modules(self, version: str) -> list[str] | None:
        """调用 php -m 获取实际加载的模块；失败返回 None。"""
        exe = self.php.php_exe(version)
        if exe is None:
            return None
        try:
            out = subprocess.run(
                [str(exe), "-m"],
                capture_output=True,
                text=True,
                timeout=20,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except OSError:
            return None
        if out.returncode != 0:
            return None
        modules = []
        in_list = False
        for line in out.stdout.splitlines():
            s = line.strip()
            if s.startswith("["):
                in_list = "PHP Modules" in s
                continue
            if in_list and s:
                modules.append(s)
        return modules


def _assigned_keys(lines: list[str]) -> list[str]:
    keys = []
    for line in lines:
        s = line.strip()
        if not s or s.startswith(";") or s.startswith("#"):
            continue
        m = _INI_KEY_RE.match(s)
        if m:
            keys.append(m.group(1).lower())
    return keys


def _set_line(lines: list[str], key: str, value: str) -> list[str]:
    prefix = key.strip().lower()
    found = False
    out: list[str] = []
    for line in lines:
        s = line.strip()
        if s and not s.startswith(";") and not s.startswith("#") and "=" in s:
            k, _, _v = s.partition("=")
            if k.strip().lower() == prefix:
                out.append(f"{key.strip()} = {value}")
                found = True
                continue
        out.append(line)
    if not found:
        if out and out[-1].strip():
            out.append("")
        out.append(f"{key.strip()} = {plain_ini_value(key, value)}")
    return out


def plain_ini_value(key: str, value: str) -> str:
    """值里带空格或特殊字符时加双引号（ini 语法）。"""
    value = value.strip()
    if key.strip().lower() in {"error_reporting", "extension_dir"}:
        return value
    if value.startswith('"') and value.endswith('"'):
        return value
    if any(c in value for c in " &~|\\"):
        return f'"{value}"'
    return value
