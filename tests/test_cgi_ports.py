"""端口分配与多版本共存的纯逻辑测试。"""

from __future__ import annotations

import pytest

from core.site_manager import cgi_port_for, cgi_port_for_version
from core.php_manager import PHPManager


def test_version_port_follows_version(sandbox):
    assert cgi_port_for_version("8.3.36") == 9803
    assert cgi_port_for_version("8.4.27") == 9804
    assert cgi_port_for_version("7.4.33") == 9704


def test_different_versions_get_different_ports(sandbox):
    ports = {cgi_port_for_version(v) for v in ("8.3.36", "8.4.27", "7.4.33")}
    assert len(ports) == 3


def test_same_version_gets_same_port(sandbox):
    assert cgi_port_for_version("8.3.36") == cgi_port_for_version("8.3.36")


def test_site_uses_version_port(sandbox):
    site = {"php": "8.4.27", "port": 8080}
    assert cgi_port_for(site) == 9804


def test_site_explicit_cgi_port_wins(sandbox):
    site = {"php": "8.4.27", "port": 8080, "cgi_port": 9500}
    assert cgi_port_for(site) == 9500


def test_cgi_port_assignment_is_stable(sandbox, fake_php):
    php = PHPManager()
    first = php.cgi_port("8.3.36")
    assert php.cgi_port("8.3.36") == first
    assert php.cgi_port("8.4.27") != first


def test_cgi_port_persisted_in_config(sandbox, fake_php):
    php = PHPManager()
    port = php.cgi_port("8.3.36")
    from core.paths import load_config

    cfg = load_config()
    assert int(cfg["php"]["cgi_ports"]["8.3.36"]) == port


@pytest.mark.parametrize("version,expected", [("8.3", 9803), ("8.4", 9804)])
def test_major_version_resolves_to_installed(sandbox, fake_php, version, expected):
    php = PHPManager()
    assert php.cgi_port(version) == expected
