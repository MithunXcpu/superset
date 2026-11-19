# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
"""NVIDIA OpenAI-compatible chat client, with an offline template fallback."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

DEFAULT_BASE_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_MODEL = "meta/llama-3.3-70b-instruct"

SYSTEM_PROMPT = (
    "You draft a one-page executive summary in markdown for an internal "
    "AI-agent rollout business case. The JSON is synthetic sample data. "
    "Keep the data_label in the first paragraph. Use only numbers present "
    "in the JSON. Do not invent customers, logos, certifications, quotas, "
    "or production results. Do not describe the author as experienced with "
    "any vendor. Explain ROI and payback with the formulas in the JSON. "
    "Close with measurements a value engineer would still collect: quality, "
    "reopen rate, and a time study. Stay under 600 words."
)


class LlmError(RuntimeError):
    """The configured LLM provider did not return a draft."""


def resolve_provider() -> str:
    """Return `nvidia` or `mock`.

    `LLM_PROVIDER=auto` uses NVIDIA when `NVIDIA_API_KEY` is set and the
    offline template otherwise.
    """
    explicit = os.environ.get("LLM_PROVIDER", "auto").strip().lower()
    if explicit == "auto":
        return "nvidia" if os.environ.get("NVIDIA_API_KEY") else "mock"
    if explicit not in {"nvidia", "mock"}:
        raise LlmError("LLM_PROVIDER must be auto, nvidia, or mock.")
    return explicit


def build_user_prompt(payload: dict[str, Any]) -> str:
    """Ask for a one-page summary grounded in the supplied metrics."""
    return (
        "Write the one-page executive summary from these sample metrics.\n\n"
        + json.dumps(payload, indent=2, sort_keys=True)
    )


def render_mock_summary(payload: dict[str, Any]) -> str:
    """Deterministic one-page summary used when no model call is available."""
    kpis = payload["kpis"]
    assumptions = payload["assumptions"]
    adoption_lines = "\n".join(
        (
            f"- {row['team']}: {row['adoption_pct']}% "
            f"({row['active_users']} of {row['licensed_users']} licensed users)"
        )
        for row in payload["adoption_by_team"]
    )
    cost_lines = "\n".join(
        (
            f"- {row['team']}: ${row['cost_before_usd']} before, "
            f"${row['cost_after_usd']} after "
            f"({row['tickets_deflected_after']} tickets deflected after go-live)"
        )
        for row in payload["cost_per_resolution_by_team"]
    )
    return f"""# Sample business case: AI agent rollout

{payload["data_label"]}. This page is a template for a value-engineering
conversation. The figures come from the local seed, not from a customer.

## Recommendation

On this sample, the after-go-live window returns ${kpis["labor_value_usd"]} of
labor value against ${kpis["investment_usd"]} of investment
(${kpis["net_value_usd"]} net). That is a {kpis["roi_pct"]}% ROI. The
implementation cost pays back in {kpis["payback_months"]} months at the
sample's monthly net, after the platform fee. Treat the payback as a reason
to inspect the handle-time assumption, not as a result to quote externally.

## What the sample measures

The seed covers January–December 2025. Go-live is {payload["go_live_date"]}.
The six months before go-live are the baseline. The six months after are the
value window. Teams in the seed are Support L1, Support L2, IT Helpdesk,
Sales Ops, and Finance Ops.

After go-live the sample shows {kpis["tickets_deflected"]} tickets deflected
and {kpis["hours_saved"]} hours saved. The blended cost per resolution moves
from ${kpis["avg_cost_before_usd"]} to ${kpis["avg_cost_after_usd"]}.

## Economics

| Item | Sample value |
| --- | --- |
| Hourly rate | ${assumptions["hourly_rate_usd"]} |
| Annual platform cost | ${assumptions["annual_platform_cost_usd"]} |
| Implementation cost | ${assumptions["implementation_cost_usd"]} |
| Platform cost in the 6-month window | ${kpis["platform_cost_in_window_usd"]} |
| Labor value | ${kpis["labor_value_usd"]} |
| Investment | ${kpis["investment_usd"]} |
| Net value | ${kpis["net_value_usd"]} |
| ROI | {kpis["roi_pct"]}% |
| Payback | {kpis["payback_months"]} months |

Labor value is hours saved after go-live times the hourly rate. Investment is
the one-time implementation cost plus the platform cost for the after window
(annual platform cost times 6/12). ROI is net value divided by that
investment. Payback is the implementation cost divided by monthly labor value
minus the monthly platform cost.

Hours saved after go-live are deflected tickets times an assumed minutes-saved
figure (15 for Support L1, 20 for Support L2, 18 for IT Helpdesk, 25 for
Sales Ops, 30 for Finance Ops).

## Adoption

Latest month in the seed (December 2025). Overall adoption is
{kpis["adoption_pct"]}%.

{adoption_lines}

## Cost per resolution

Weighted by tickets closed (deflected plus human-resolved):

{cost_lines}

## What to collect before this leaves the demo

- A time study that replaces the assumed minutes per deflected ticket.
- Reopen and escalation rates, so deflection is not counted when the work
  comes back.
- A quality check (CSAT or QA sample) for agent-handled tickets.
- The real contract: usage fees, not only the flat annual figure in the seed.

Until those are measured, this page is a way to show the shape of the
business case, not a claim about a deployment.
"""


def call_nvidia(prompt: str) -> str:
    """Call NVIDIA's OpenAI-compatible chat completions API."""
    api_key = os.environ.get("NVIDIA_API_KEY", "").strip()
    if not api_key:
        raise LlmError("NVIDIA_API_KEY is not set.")
    base_url = os.environ.get("LLM_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    model = os.environ.get("LLM_MODEL", DEFAULT_MODEL)
    body = {
        "model": model,
        "temperature": 0.2,
        "max_tokens": 1200,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    }
    request = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310
            parsed = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise LlmError(f"NVIDIA API returned HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise LlmError(f"NVIDIA API request failed: {exc.reason}") from exc
    try:
        content = parsed["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LlmError("NVIDIA API response did not include a message.") from exc
    if not isinstance(content, str) or not content.strip():
        raise LlmError("NVIDIA API returned an empty message.")
    return content.strip()


def draft_summary(payload: dict[str, Any]) -> tuple[str, str]:
    """Return markdown and a source tag (`mock` or `nvidia`).

    A failed NVIDIA call falls back to the offline template unless
    `LLM_FALLBACK=error`.
    """
    provider = resolve_provider()
    prompt = build_user_prompt(payload)
    if provider == "mock":
        body = render_mock_summary(payload)
        source = "mock"
    else:
        try:
            body = call_nvidia(prompt)
            source = "nvidia"
        except LlmError as exc:
            if os.environ.get("LLM_FALLBACK", "mock").strip().lower() == "error":
                raise
            body = (
                f"The NVIDIA draft was unavailable ({exc}). "
                "The offline template follows.\n\n" + render_mock_summary(payload)
            )
            source = "mock"
    banner = f"> Data label: {payload['data_label']}\n> Narrative source: {source}\n\n"
    return banner + body, source
