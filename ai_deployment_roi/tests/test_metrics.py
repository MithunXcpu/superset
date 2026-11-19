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
"""Checks for the synthetic seed and the business-case formulas."""

from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from metrics import (  # noqa: E402
    build_rows,
    business_case,
    DATA_LABEL,
    narrative_payload,
    render_sql,
    TEAMS,
)


def test_seed_shape_and_label() -> None:
    """Five teams, twelve months, and a synthetic label on every row."""
    rows = build_rows()
    assert len(rows) == len(TEAMS) * 12
    assert {row.team for row in rows} == {team.name for team in TEAMS}
    assert all(row.data_label == DATA_LABEL for row in rows)
    assert sum(row.phase == "before" for row in rows) == len(TEAMS) * 6
    assert sum(row.phase == "after" for row in rows) == len(TEAMS) * 6


def test_ticket_and_adoption_constraints() -> None:
    """Deflection cannot exceed opened tickets, and adoption stays in range."""
    for row in build_rows():
        closed = row.tickets_deflected + row.tickets_resolved_by_human
        assert closed == row.tickets_opened
        assert 0 <= row.tickets_deflected < row.tickets_opened
        assert 0 <= row.active_users <= row.licensed_users
        expected = "after" if row.period_month >= date(2025, 7, 1) else "before"
        assert row.phase == expected


def test_after_period_is_the_improvement() -> None:
    """The sample shows more deflection, more hours, and a lower unit cost."""
    case = business_case()
    rows = build_rows()
    before_hours = sum(
        (row.hours_saved for row in rows if row.phase == "before"),
        Decimal(0),
    )
    assert case.hours_saved > before_hours
    assert case.avg_cost_after_usd < case.avg_cost_before_usd
    assert case.roi_pct > 0
    assert Decimal("0") < case.payback_months < Decimal("12")
    assert Decimal("0") < case.adoption_pct <= Decimal("100")


def test_known_sample_totals() -> None:
    """Lock the seed so the dashboard and the narrative stay on the same figures."""
    case = business_case()
    assert case.tickets_deflected == 15734
    assert case.hours_saved == Decimal("4559.38")
    assert case.labor_value_usd == Decimal("387547.30")
    assert case.investment_usd == Decimal("165000.00")
    assert case.net_value_usd == Decimal("222547.30")
    assert case.roi_pct == Decimal("134.9")
    assert case.payback_months == Decimal("1.5")
    assert case.avg_cost_before_usd == Decimal("30.10")
    assert case.avg_cost_after_usd == Decimal("15.40")
    assert case.adoption_pct == Decimal("83.1")


def test_sql_file_matches_the_generator() -> None:
    """The committed seed is the generator output."""
    sql_path = Path(__file__).resolve().parents[1] / "sql" / "01_synthetic_ai_roi.sql"
    assert sql_path.read_text(encoding="utf-8") == render_sql()


def test_payload_exposes_only_labeled_sample_facts() -> None:
    """The prompt payload carries the label, formulas, and team breakdowns."""
    payload = narrative_payload()
    assert payload["data_label"] == DATA_LABEL
    assert "roi_pct" in payload["formulas"]
    assert len(payload["adoption_by_team"]) == 5
    assert len(payload["cost_per_resolution_by_team"]) == 5
    teams = {row["team"] for row in payload["adoption_by_team"]}
    assert "Support L1" in teams
