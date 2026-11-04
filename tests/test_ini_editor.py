"""php.ini 编辑器：常用设置读写、扩展开关、备份。"""

from __future__ import annotations

import pytest

from core.ini_editor import IniEditor


@pytest.fixture()
def editor(sandbox, fake_php):
    return IniEditor()


def test_parse_value(editor):
    text = "memory_limit = 256M\n;post_max_size = 8M\ndate.timezone = \"Asia/Shanghai\"\n"
    assert IniEditor.parse_value(text, "memory_limit") == "256M"
    assert IniEditor.parse_value(text, "post_max_size") is None  # 注释掉的不算
    assert IniEditor.parse_value(text, "date.timezone") == "Asia/Shanghai"
    assert IniEditor.parse_value(text, "missing") is None


def test_get_and_set_value(editor, fake_php):
    editor.set_value("8.3.36", "memory_limit", "512M")
    assert editor.get_value("8.3.36", "memory_limit") == "512M"


def test_set_value_appends_when_missing(editor, fake_php):
    editor.set_value("8.3.36", "max_input_vars", "3000")
    assert editor.get_value("8.3.36", "max_input_vars") == "3000"


def test_set_values_multiple(editor, fake_php):
    editor.set_values("8.3.36", {"memory_limit": "1G", "date.timezone": "UTC"})
    assert editor.get_value("8.3.36", "memory_limit") == "1G"
    assert editor.get_value("8.3.36", "date.timezone") == "UTC"


def test_save_creates_backup(editor, fake_php):
    backup = editor.save("8.3.36", "memory_limit = 1M\n")
    assert backup.exists()
    assert backup.name.startswith("php.ini.bak-")
    assert editor.get_value("8.3.36", "memory_limit") == "1M"


def test_extension_enabled_detection(editor, fake_php):
    text = "extension=curl\n;extension=gd\n# comment\nextension = mbstring\n"
    assert editor.extension_enabled(text, "curl") is True
    assert editor.extension_enabled(text, "gd") is False
    assert editor.extension_enabled(text, "mbstring") is True
    assert editor.extension_enabled(text, "zip") is False


def test_enabled_extensions(editor, fake_php):
    assert editor.enabled_extensions("8.3.36") == set()


def test_set_extension_enables(editor, fake_php):
    editor.set_extension("8.3.36", "curl", True)
    assert "curl" in editor.enabled_extensions("8.3.36")


def test_set_extension_disables(editor, fake_php):
    editor.set_extension("8.3.36", "curl", True)
    editor.set_extension("8.3.36", "curl", False)
    assert "curl" not in editor.enabled_extensions("8.3.36")


def test_set_extension_is_idempotent(editor, fake_php):
    editor.set_extension("8.3.36", "curl", True)
    editor.set_extension("8.3.36", "curl", True)
    text = editor.read("8.3.36")
    assert text.count("extension=curl") == 1


def test_set_extension_unknown_raises(editor, fake_php):
    with pytest.raises(ValueError):
        editor.set_extension("8.3.36", "no_such_ext", True)


def test_php_ini_of_missing_version_raises(editor):
    with pytest.raises(FileNotFoundError):
        editor.read("9.9.9")
