# tests/agent/test_paritok_proxy.py
import yaml
import pytest

from repo_debug_agent.agent.paritok_proxy import ParitokProxyManager
from repo_debug_agent.context_retrieval.paritok_adaptor import ParitokConfig
from repo_debug_agent.exceptions import ParitokProxyError


def test_base_url_reflects_host_and_port():
    manager = ParitokProxyManager(host="127.0.0.1", port=9090)
    assert manager.base_url == "http://127.0.0.1:9090"


def test_start_raises_when_gpu_server_enabled_without_api_key(monkeypatch):
    monkeypatch.setattr(
        "repo_debug_agent.agent.paritok_proxy.get_paritok_config",
        lambda: ParitokConfig(api_key="", use_gpu_server=True),
    )
    manager = ParitokProxyManager()

    with pytest.raises(ParitokProxyError, match="paritok.com"):
        manager.start()


def test_write_config_file_reflects_settings(tmp_path):
    config = ParitokConfig(api_key="pk_live_test123", use_gpu_server=True)
    path = ParitokProxyManager._write_config_file(config)
    try:
        written = yaml.safe_load(path.read_text())
        assert written["use_gpu_server"] is True
        assert written["gpu_server"]["api_key"] == "pk_live_test123"
    finally:
        path.unlink(missing_ok=True)


def test_stop_is_safe_when_never_started():
    manager = ParitokProxyManager()
    manager.stop()  # should not raise
    assert manager._process is None