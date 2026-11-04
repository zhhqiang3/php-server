"""站点弹窗离屏截图。"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "windows")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PyQt6.QtWidgets import QApplication  # noqa: E402

app = QApplication([])
from gui.appearance import apply_appearance  # noqa: E402

OUT = Path(os.environ.get("SHOT_DIR", ROOT / "shots"))
OUT.mkdir(parents=True, exist_ok=True)


def main() -> None:
    theme = os.environ.get("SHOT_THEME", "深色")
    apply_appearance(app, theme=theme, font_size=10)

    from core.php_manager import PHPManager
    from core.site_manager import SiteManager
    from gui.site_dialog import SiteDialog

    sites = SiteManager()
    dlg = SiteDialog(None, sites, PHPManager())
    dlg.name.setText("demo")
    dlg.resize(520, dlg.sizeHint().height())
    dlg.show()
    app.processEvents()
    path = OUT / f"{theme}-site-dialog.png"
    dlg.grab().save(str(path))
    print(f"saved {path}")


if __name__ == "__main__":
    main()
