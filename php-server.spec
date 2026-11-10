# -*- mode: python ; coding: utf-8 -*-
# PyInstaller 打包配置：单文件 exe，不带控制台窗口
a = Analysis(
    ["gui/main.py"],
    pathex=[],
    binaries=[],
    datas=[("assets/icon.ico", ".")],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="php-server",
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon="assets/icon.ico",
)
