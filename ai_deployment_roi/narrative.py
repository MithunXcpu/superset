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
"""Draft a one-page business-case summary from the synthetic ROI metrics.

Reads `v_business_case` and the team views when `AI_ROI_DATABASE_URL` is set.
`--offline` uses the same figures from `metrics.py` so the script runs
without Postgres or an API key.
"""

from __future__ import annotations

import argparse
import os
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

from llm_client import draft_summary, LlmError
from metrics import narrative_payload


def _scaled(value: Any) -> str:
    """Render a numeric database value the same way the seed payload does."""
    if isinstance(value, Decimal):
        return format(value, "f")
    return str(value)


def load_metrics_from_database(url: str) -> dict[str, Any]:
    """Read the headline views from the demo Postgres database."""
    try:
        import psycopg2
        import psycopg2.extras
    except ImportError as exc:
        raise SystemExit(
            "psycopg2 is required to read Postgres. "
            "Install ai_deployment_roi/requirements.txt or pass --offline."
        ) from exc

    with psycopg2.connect(url) as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("SELECT * FROM v_business_case")
            case_row = cursor.fetchone()
            if case_row is None:
                raise SystemExit("v_business_case returned no rows.")
            case = dict(case_row)
            cursor.execute(
                "SELECT team, period_month, active_users, licensed_users, "
                "adoption_pct FROM v_adoption_by_team ORDER BY team"
            )
            adoption = [dict(row) for row in cursor.fetchall()]
            cursor.execute(
                "SELECT team, phase, tickets_deflected, hours_saved "
                "FROM v_cost_by_team_phase ORDER BY team, phase"
            )
            detail = [dict(row) for row in cursor.fetchall()]
            cursor.execute(
                "SELECT team, cost_before_usd, cost_after_usd "
                "FROM v_cost_before_after ORDER BY team"
            )
            costs = [dict(row) for row in cursor.fetchall()]

    after_detail = {row["team"]: row for row in detail if row["phase"] == "after"}
    offline = narrative_payload()
    cost_rows = []
    for row in costs:
        team_after = after_detail[row["team"]]
        cost_rows.append(
            {
                "team": row["team"],
                "cost_before_usd": _scaled(row["cost_before_usd"]),
                "cost_after_usd": _scaled(row["cost_after_usd"]),
                "tickets_deflected_after": int(team_after["tickets_deflected"]),
                "hours_saved_after": _scaled(team_after["hours_saved"]),
            }
        )
    go_live = case["go_live_date"]
    return {
        "data_label": case["data_label"],
        "go_live_date": go_live.isoformat()
        if hasattr(go_live, "isoformat")
        else go_live,
        "window": offline["window"],
        "assumptions": {
            "hourly_rate_usd": _scaled(case["hourly_rate_usd"]),
            "annual_platform_cost_usd": _scaled(case["annual_platform_cost_usd"]),
            "implementation_cost_usd": _scaled(case["implementation_cost_usd"]),
            "minutes_saved_per_deflected_ticket": offline["assumptions"][
                "minutes_saved_per_deflected_ticket"
            ],
        },
        "kpis": {
            "tickets_deflected": int(case["tickets_deflected"]),
            "hours_saved": _scaled(case["hours_saved"]),
            "months_after": int(case["months_after"]),
            "labor_value_usd": _scaled(case["labor_value_usd"]),
            "platform_cost_in_window_usd": _scaled(case["platform_cost_in_window_usd"]),
            "investment_usd": _scaled(case["investment_usd"]),
            "net_value_usd": _scaled(case["net_value_usd"]),
            "roi_pct": _scaled(case["roi_pct"]),
            "payback_months": _scaled(case["payback_months"]),
            "avg_cost_before_usd": _scaled(case["avg_cost_before_usd"]),
            "avg_cost_after_usd": _scaled(case["avg_cost_after_usd"]),
            "adoption_pct": _scaled(case["adoption_pct"]),
        },
        "adoption_by_team": [
            {
                "team": row["team"],
                "period_month": (
                    row["period_month"].isoformat()
                    if hasattr(row["period_month"], "isoformat")
                    else str(row["period_month"])
                ),
                "active_users": int(row["active_users"]),
                "licensed_users": int(row["licensed_users"]),
                "adoption_pct": _scaled(row["adoption_pct"]),
            }
            for row in adoption
        ],
        "cost_per_resolution_by_team": cost_rows,
        "formulas": offline["formulas"],
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Draft a one-page AI deployment business case from the sample ROI metrics."
        )
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Use the in-repo synthetic metrics instead of Postgres.",
    )
    parser.add_argument(
        "--database-url",
        default=os.environ.get("AI_ROI_DATABASE_URL", ""),
        help="Postgres URL. Defaults to AI_ROI_DATABASE_URL.",
    )
    parser.add_argument(
        "--output",
        default="-",
        help="Write markdown to this path, or - for stdout.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Load metrics, draft the summary, and write markdown."""
    args = parse_args(argv)
    if args.offline:
        payload = narrative_payload()
    elif args.database_url:
        payload = load_metrics_from_database(args.database_url)
    else:
        print("Set AI_ROI_DATABASE_URL or pass --offline.", file=sys.stderr)
        return 2
    try:
        markdown, source = draft_summary(payload)
    except LlmError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"narrative_source={source}", file=sys.stderr)
    if args.output == "-":
        sys.stdout.write(markdown)
        if not markdown.endswith("\n"):
            sys.stdout.write("\n")
    else:
        Path(args.output).write_text(markdown, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
