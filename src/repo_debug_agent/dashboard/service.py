"""
DashboardService: single public entrypoint for Phase 12.
"""

from __future__ import annotations

from pathlib import Path

from repo_debug_agent.dashboard.builder import build_dashboard
from repo_debug_agent.dashboard.models import UsageDashboard
from repo_debug_agent.dashboard.report import render_html, render_markdown
from repo_debug_agent.test_loop.models import TestLoopResult


class DashboardService:
    def build(self, result: TestLoopResult) -> UsageDashboard:
        return build_dashboard(result)

    def render_markdown(self, result: TestLoopResult) -> str:
        return render_markdown(self.build(result))

    def render_html(self, result: TestLoopResult) -> str:
        return render_html(self.build(result))

    def write_report(self, result: TestLoopResult, output_dir: Path) -> dict[str, Path]:
        """Write both a JSON dashboard (for Phase 13's future API) and an
        HTML dashboard (something to literally show a judge) to disk."""
        output_dir.mkdir(parents=True, exist_ok=True)
        dashboard = self.build(result)

        json_path = output_dir / "usage_dashboard.json"
        json_path.write_text(dashboard.model_dump_json(indent=2), encoding="utf-8")

        html_path = output_dir / "usage_dashboard.html"
        html_path.write_text(render_html(dashboard), encoding="utf-8")

        return {"json": json_path, "html": html_path}