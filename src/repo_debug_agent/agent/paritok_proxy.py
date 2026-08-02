"""
Manages a locally-running `paritok proxy` process, configured (per
paritok_adaptor.py's original notes) to route compression through
Paritok's hosted GPU server — the mode required for hackathon judging,
since usage is verified against the Paritok account/API key on their
dashboard.

WHY PROXY MODE, NOT SDK MODE:
Paritok ships two integration modes:
  1. SDK mode — `paritok.ParitokClient(client)` wraps a client object
     directly. Inspecting the installed `paritok` package: this wrapper
     hardcodes `self._parent._client.messages.create(**kwargs)` — it
     only supports Anthropic-shaped clients (`client.messages.create`).
  2. Proxy mode — run `paritok proxy`, point `OPENAI_BASE_URL` /
     `ANTHROPIC_BASE_URL` at it. Paritok's own README calls this the
     "primary, recommended" mode, and its proxy has adapters for BOTH
     OpenAI and Anthropic request shapes.

This project's LLM client is `openai.OpenAI()` (Chat Completions:
`client.chat.completions.create()`), which SDK mode cannot wrap. So
Phase 9 runs the proxy locally and points the existing OpenAI client's
`base_url` at it — no change to the LLM provider, and it's the
integration mode Paritok itself recommends.
"""

from __future__ import annotations

import atexit
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx
import yaml

from repo_debug_agent.context_retrieval.paritok_adaptor import ParitokConfig, get_paritok_config
from repo_debug_agent.core.logger import logger
from repo_debug_agent.exceptions import ParitokProxyError


class ParitokProxyManager:
    """Starts, health-checks, queries, and cleanly stops a `paritok proxy` subprocess."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8080, startup_timeout: float = 20.0):
        self._host = host
        self._port = port
        self._startup_timeout = startup_timeout
        self._process: subprocess.Popen | None = None
        self._config_path: Path | None = None

    @property
    def base_url(self) -> str:
        return f"http://{self._host}:{self._port}"

    def start(self) -> None:
        """Idempotent: does nothing if already running."""
        if self._process is not None:
            return

        config = get_paritok_config()
        if config.use_gpu_server and not config.api_key:
            raise ParitokProxyError(
                "paritok_use_gpu_server is True but no Paritok API key is configured. "
                "Sign up at https://paritok.com, create an API key from the dashboard, "
                "and set PARITOK_API_KEY=pk_live_... in .env before running Phase 9."
            )

        self._config_path = self._write_config_file(config)

        cmd = [
            sys.executable, "-m", "paritok.cli", "proxy",
            "--host", self._host,
            "--port", str(self._port),
            "--config-file", str(self._config_path),
        ]
        logger.info(f"Starting Paritok proxy (use_gpu_server={config.use_gpu_server}): {' '.join(cmd)}")
        self._process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
        atexit.register(self.stop)
        self._wait_until_healthy()

    @staticmethod
    def _write_config_file(config: ParitokConfig) -> Path:
        """Write a minimal paritok.yaml reflecting OUR settings (Phase 1's Settings),
        so the proxy doesn't rely on ambient environment variables."""
        fd, path = tempfile.mkstemp(prefix="paritok_proxy_", suffix=".yaml")
        yaml_content = {
            "use_gpu_server": config.use_gpu_server,
            "gpu_server": {"api_key": config.api_key},
        }
        with open(fd, "w", encoding="utf-8") as f:
            yaml.safe_dump(yaml_content, f)
        return Path(path)

    def _wait_until_healthy(self) -> None:
        deadline = time.monotonic() + self._startup_timeout
        last_error: Exception | None = None
        while time.monotonic() < deadline:
            if self._process is not None and self._process.poll() is not None:
                output = self._process.stdout.read() if self._process.stdout else ""
                raise ParitokProxyError(f"Paritok proxy exited early (before becoming healthy):\n{output}")
            try:
                response = httpx.get(f"{self.base_url}/health", timeout=2.0)
                if response.status_code == 200:
                    logger.info(f"Paritok proxy healthy at {self.base_url}")
                    return
            except httpx.HTTPError as exc:
                last_error = exc
            time.sleep(0.5)
        raise ParitokProxyError(
            f"Paritok proxy did not become healthy within {self._startup_timeout}s: {last_error}"
        )

    def stats(self) -> dict:
        """Cumulative session stats from the proxy's `/stats` endpoint."""
        response = httpx.get(f"{self.base_url}/stats", timeout=5.0)
        response.raise_for_status()
        return response.json()

    def stop(self) -> None:
        if self._process is not None and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                self._process.kill()
        self._process = None
        if self._config_path is not None and self._config_path.exists():
            self._config_path.unlink(missing_ok=True)
        self._config_path = None

    def __enter__(self) -> "ParitokProxyManager":
        self.start()
        return self

    def __exit__(self, *exc_info) -> None:
        self.stop()