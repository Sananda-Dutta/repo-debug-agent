"""
Paritok integration point.

⚠️ IMPORTANT ARCHITECTURAL NOTE: Paritok is NOT a standalone
compress(text) -> str function we call mid-pipeline. It's a
middleware/proxy that compresses requests at the moment they're sent
to the LLM (via paritok.ParitokClient wrapping the actual API client,
or via the `paritok proxy` server). See:
https://github.com/Paritok-official/paritok-4b-v1

Because of that, Paritok is NOT wired up as a TokenCompressor here in
Phase 8 — there's no LLM call yet at this point in the pipeline. The
real integration happens in Phase 9 (LLM Agent Layer), where we wrap
our actual LLM client with paritok.ParitokClient, configured to route
through Paritok's HOSTED GPU SERVER (required for hackathon judging —
usage is verified against your Paritok account/API key on their
dashboard, not self-hosted Ollama).

This module exists in Phase 8 only to:
1. Hold the config helper (`get_paritok_config`) both this phase and
   Phase 9 can share.
2. Document the integration point clearly so Phase 9 wires it
   correctly instead of guessing.

Setup (do this now, so Phase 9 can just import and go):
    pip install -e ".[paritok]"
    # Get an API key: https://paritok.com -> dashboard -> API keys
    # Put it in .env as PARITOK_API_KEY=pk_live_...
"""

from dataclasses import dataclass

from repo_debug_agent.config.settings import get_settings


@dataclass
class ParitokConfig:
    api_key: str
    use_gpu_server: bool


def get_paritok_config() -> ParitokConfig:
    """Read Paritok configuration from application settings (Phase 1's Settings)."""
    settings = get_settings()
    return ParitokConfig(
        api_key=settings.paritok_api_key,
        use_gpu_server=settings.paritok_use_gpu_server,
    )