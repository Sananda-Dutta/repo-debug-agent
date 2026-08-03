"""
Phase 12: renders a UsageDashboard as Markdown (for a Devpost writeup)
or a small, self-contained HTML file — a literal "dashboard" a judge
can open directly in a browser, no server or JS framework required.
"""

from __future__ import annotations

from repo_debug_agent.dashboard.models import UsageDashboard


def render_markdown(dashboard: UsageDashboard) -> str:
    lines = [
        "# Token Usage Dashboard",
        "",
        f"**Result:** {'Fixed' if dashboard.success else 'Not resolved'} "
        f"in {dashboard.total_iterations} iteration(s)",
        f"**Failing tests:** {dashboard.baseline_failing_tests} -> {dashboard.final_failing_tests}",
        "",
        "## Totals",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Local compression (Phase 8) | {dashboard.total_baseline_tokens} -> "
        f"{dashboard.total_compressed_tokens} tokens ({dashboard.overall_local_compression_ratio:.1%} reduction) |",
        f"| Paritok hosted-GPU requests | {dashboard.total_paritok_requests} |",
        f"| Paritok tokens saved | {dashboard.total_paritok_tokens_saved} |",
        f"| Paritok estimated cost saved | {dashboard.total_paritok_cost_saved_usd} |",
        "",
        "## Outcomes by iteration",
        "",
        "| # | Outcome | Local ratio | Paritok saved | Paritok cost saved |",
        "|---|---|---|---|---|",
    ]
    for it in dashboard.iterations:
        lines.append(
            f"| {it.iteration} | {it.outcome} | {it.local_compression_ratio:.1%} | "
            f"{it.paritok_tokens_saved} tok | {it.paritok_cost_saved_usd} |"
        )
    return "\n".join(lines) + "\n"


_HTML_TEMPLATE = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Token Usage Dashboard</title>
<style>
body {{ font-family: -apple-system, sans-serif; max-width: 760px; margin: 40px auto; color: #1a1a1a; }}
h1 {{ font-size: 1.4rem; }}
table {{ border-collapse: collapse; width: 100%; margin: 16px 0; }}
th, td {{ text-align: left; padding: 6px 10px; border-bottom: 1px solid #ddd; font-size: 0.9rem; }}
th {{ background: #f5f5f5; }}
.status {{ font-weight: 600; }}
.status.ok {{ color: #1a7f37; }}
.status.fail {{ color: #cf222e; }}
</style></head><body>
<h1>Token Usage Dashboard</h1>
<p class="status {status_class}">{status_text}</p>
<p>Failing tests: {baseline_failing} -&gt; {final_failing} across {total_iterations} iteration(s)</p>
<table>
<tr><th>Metric</th><th>Value</th></tr>
<tr><td>Local compression (Phase 8)</td><td>{total_baseline} -&gt; {total_compressed} tokens ({local_ratio:.1%} reduction)</td></tr>
<tr><td>Paritok hosted-GPU requests</td><td>{paritok_requests}</td></tr>
<tr><td>Paritok tokens saved</td><td>{paritok_saved}</td></tr>
<tr><td>Paritok estimated cost saved</td><td>{paritok_cost}</td></tr>
</table>
<h2>Outcomes by iteration</h2>
<table>
<tr><th>#</th><th>Outcome</th><th>Local ratio</th><th>Paritok saved</th><th>Paritok cost saved</th></tr>
{rows}
</table>
</body></html>
"""


def render_html(dashboard: UsageDashboard) -> str:
    rows = "\n".join(
        f"<tr><td>{it.iteration}</td><td>{it.outcome}</td><td>{it.local_compression_ratio:.1%}</td>"
        f"<td>{it.paritok_tokens_saved}</td><td>{it.paritok_cost_saved_usd}</td></tr>"
        for it in dashboard.iterations
    )
    return _HTML_TEMPLATE.format(
        status_class="ok" if dashboard.success else "fail",
        status_text="Fixed" if dashboard.success else "Not resolved",
        baseline_failing=dashboard.baseline_failing_tests,
        final_failing=dashboard.final_failing_tests,
        total_iterations=dashboard.total_iterations,
        total_baseline=dashboard.total_baseline_tokens,
        total_compressed=dashboard.total_compressed_tokens,
        local_ratio=dashboard.overall_local_compression_ratio,
        paritok_requests=dashboard.total_paritok_requests,
        paritok_saved=dashboard.total_paritok_tokens_saved,
        paritok_cost=dashboard.total_paritok_cost_saved_usd,
        rows=rows or "<tr><td colspan=\"5\">No iterations were needed.</td></tr>",
    )