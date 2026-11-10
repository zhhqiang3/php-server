"""从 assets/icon.svg 渲染 ico / png 图标（开发期一次性工具）。"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QBuffer, QByteArray, Qt
from PyQt6.QtGui import QColor, QImage, QPainter
from PyQt6.QtSvg import QSvgRenderer

ROOT = Path(__file__).resolve().parent.parent
SVG = ROOT / "assets" / "icon.svg"
OUT = ROOT / "assets"


def render(size: int) -> QImage:
    renderer = QSvgRenderer(str(SVG))
    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(p)
    p.end()
    return img


def write_png(size: int) -> None:
    render(size).save(str(OUT / f"icon-{size}.png"), "PNG")


def write_ico() -> None:
    # Windows ico：多尺寸打包，PyInstaller 取 256 作大图、16 作小图
    import struct

    sizes = [16, 24, 32, 48, 64, 128, 256]
    images = []
    for s in sizes:
        img = render(s)
        data = QByteArray()
        buf = QBuffer(data)
        buf.open(QBuffer.OpenModeFlag.WriteOnly)
        img.save(buf, "PNG")
        buf.close()
        images.append((s, bytes(data)))

    # ICO 头：6 字节文件头 + 每图 16 字节目录项 + PNG 数据
    offset = 6 + 16 * len(images)
    out = struct.pack("<HHH", 0, 1, len(images))
    for s, png in images:
        out += struct.pack("<BBBBHHII", s % 256, s % 256, 0, 0, 1, 32, len(png), offset)
        offset += len(png)
    for _, png in images:
        out += png

    (OUT / "icon.ico").write_bytes(out)


if __name__ == "__main__":
    for s in (16, 24, 32, 48, 64, 128, 256):
        write_png(s)
    write_ico()
    print("done:", *(f"icon-{s}.png" for s in (16, 24, 32, 48, 64, 128, 256)), "icon.ico")
