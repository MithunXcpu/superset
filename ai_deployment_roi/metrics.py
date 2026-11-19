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
"""Synthetic AI-agent rollout metrics and the Postgres seed that stores them.

Every figure in this module is generated sample data for a local demo.
It is not a customer measurement.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

DATA_LABEL = "SYNTHETIC DEMO — not a real customer or deployment"

HOURLY_RATE_USD = Decimal("85.00")
ANNUAL_PLATFORM_COST_USD = Decimal("180000.00")
IMPLEMENTATION_COST_USD = Decimal("75000.00")
GO_LIVE_DATE = date(2025, 7, 1)

BEFORE_MONTHS = tuple(date(2025, month, 1) for month in range(1, 7))
AFTER_MONTHS = tuple(date(2025, month, 1) for month in range(7, 13))
BEFORE_FACTORS = tuple(
    Decimal(value) for value in ("0.95", "1.00", "1.02", "0.98", "1.01", "1.04")
)
AFTER_FACTORS = tuple(
    Decimal(value) for value in ("0.70", "0.85", "1.00", "1.00", "1.05", "1.08")
)

FORMULAS = {
    "labor_value_usd": "hours saved after go-live × hourly rate",
    "platform_cost_in_window_usd": "annual platform cost × after months / 12",
    "investment_usd": "implementation cost + platform cost in the after window",
    "net_value_usd": "labor value − investment",
    "roi_pct": "net value / investment × 100",
    "payback_months": (
        "implementation cost / (monthly labor value − monthly platform cost)"
    ),
    "avg_cost_per_resolution_usd": (
        "cost per resolution weighted by deflected tickets + human resolutions"
    ),
    "adoption_pct": "active users / licensed users in the latest month × 100",
    "hours_saved_after": (
        "deflected tickets × assumed minutes saved per deflected ticket / 60"
    ),
}


@dataclass(frozen=True)
class TeamProfile:
    """Steady-state sample volumes for one internal team."""

    name: str
    tickets_opened: int
    deflected_before: int
    deflected_after: int
    hours_before: Decimal
    minutes_saved_per_deflected_ticket: Decimal
    cost_before_usd: Decimal
    cost_after_usd: Decimal
    licensed_users: int
    active_before: int
    active_after: int


TEAMS = (
    TeamProfile(
        "Support L1",
        4800,
        150,
        1600,
        Decimal("40"),
        Decimal("15"),
        Decimal("24.00"),
        Decimal("9.00"),
        48,
        10,
        41,
    ),
    TeamProfile(
        "Support L2",
        1400,
        40,
        380,
        Decimal("20"),
        Decimal("20"),
        Decimal("38.00"),
        Decimal("21.00"),
        22,
        6,
        16,
    ),
    TeamProfile(
        "IT Helpdesk",
        1800,
        60,
        520,
        Decimal("25"),
        Decimal("18"),
        Decimal("31.00"),
        Decimal("14.00"),
        30,
        8,
        24,
    ),
    TeamProfile(
        "Sales Ops",
        600,
        20,
        180,
        Decimal("15"),
        Decimal("25"),
        Decimal("45.00"),
        Decimal("28.00"),
        18,
        4,
        12,
    ),
    TeamProfile(
        "Finance Ops",
        350,
        10,
        90,
        Decimal("12"),
        Decimal("30"),
        Decimal("52.00"),
        Decimal("36.00"),
        12,
        3,
        7,
    ),
)


@dataclass(frozen=True)
class MonthlyRow:
    """One team-month of the synthetic fact table."""

    period_month: date
    team: str
    phase: str
    tickets_opened: int
    tickets_deflected: int
    tickets_resolved_by_human: int
    hours_saved: Decimal
    cost_per_resolution_usd: Decimal
    active_users: int
    licensed_users: int
    data_label: str = DATA_LABEL


@dataclass(frozen=True)
class BusinessCase:
    """Headline figures for the after-go-live window."""

    data_label: str
    hourly_rate_usd: Decimal
    annual_platform_cost_usd: Decimal
    implementation_cost_usd: Decimal
    go_live_date: date
    tickets_deflected: int
    hours_saved: Decimal
    months_after: int
    labor_value_usd: Decimal
    platform_cost_in_window_usd: Decimal
    investment_usd: Decimal
    net_value_usd: Decimal
    roi_pct: Decimal
    payback_months: Decimal
    avg_cost_before_usd: Decimal
    avg_cost_after_usd: Decimal
    adoption_pct: Decimal


def _money(value: Decimal) -> Decimal:
    """Round a money amount half-up to cents."""
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _tenths(value: Decimal) -> Decimal:
    """Round a rate half-up to one decimal place."""
    return value.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


def _whole(value: Decimal) -> int:
    """Round a count half-up to an integer."""
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _sql_string(value: str) -> str:
    """Quote a string for a static INSERT."""
    return "'" + value.replace("'", "''") + "'"


def build_rows() -> tuple[MonthlyRow, ...]:
    """Expand team profiles into 12 months of before/after sample rows."""
    rows: list[MonthlyRow] = []
    phases = (
        ("before", BEFORE_MONTHS, BEFORE_FACTORS),
        ("after", AFTER_MONTHS, AFTER_FACTORS),
    )
    for phase, months, factors in phases:
        for period_month, factor in zip(months, factors, strict=True):
            for team in TEAMS:
                base_deflected = (
                    team.deflected_after if phase == "after" else team.deflected_before
                )
                deflected = min(
                    _whole(Decimal(base_deflected) * factor),
                    team.tickets_opened - 1,
                )
                if phase == "after":
                    hours = _money(
                        Decimal(deflected)
                        * team.minutes_saved_per_deflected_ticket
                        / Decimal(60)
                    )
                    span = min(factor, Decimal("1"))
                    cost = _money(
                        team.cost_before_usd
                        + (team.cost_after_usd - team.cost_before_usd) * span
                    )
                    base_active = team.active_after
                else:
                    hours = _money(team.hours_before * factor)
                    cost = team.cost_before_usd
                    base_active = team.active_before
                active = min(
                    team.licensed_users,
                    max(0, _whole(Decimal(base_active) * factor)),
                )
                rows.append(
                    MonthlyRow(
                        period_month=period_month,
                        team=team.name,
                        phase=phase,
                        tickets_opened=team.tickets_opened,
                        tickets_deflected=deflected,
                        tickets_resolved_by_human=team.tickets_opened - deflected,
                        hours_saved=hours,
                        cost_per_resolution_usd=cost,
                        active_users=active,
                        licensed_users=team.licensed_users,
                    )
                )
    return tuple(rows)


def _weighted_cost(rows: tuple[MonthlyRow, ...] | list[MonthlyRow]) -> Decimal:
    """Volume-weighted average cost per resolution."""
    numerator = sum(
        (
            row.cost_per_resolution_usd
            * (row.tickets_deflected + row.tickets_resolved_by_human)
            for row in rows
        ),
        Decimal(0),
    )
    denominator = sum(
        (row.tickets_deflected + row.tickets_resolved_by_human for row in rows),
        0,
    )
    return _money(numerator / Decimal(denominator))


def business_case(rows: tuple[MonthlyRow, ...] | None = None) -> BusinessCase:
    """Compute ROI, payback, and the other headline sample figures."""
    source = build_rows() if rows is None else rows
    after = [row for row in source if row.phase == "after"]
    before = [row for row in source if row.phase == "before"]
    hours_saved = sum((row.hours_saved for row in after), Decimal(0))
    months_after = len({row.period_month for row in after})
    labor_raw = hours_saved * HOURLY_RATE_USD
    platform_raw = ANNUAL_PLATFORM_COST_USD * Decimal(months_after) / Decimal(12)
    investment_raw = IMPLEMENTATION_COST_USD + platform_raw
    net_raw = labor_raw - investment_raw
    monthly_net = (labor_raw / Decimal(months_after)) - (
        ANNUAL_PLATFORM_COST_USD / Decimal(12)
    )
    latest = max(row.period_month for row in source)
    latest_rows = [row for row in source if row.period_month == latest]
    adoption = _tenths(
        Decimal(sum(row.active_users for row in latest_rows))
        * Decimal(100)
        / Decimal(sum(row.licensed_users for row in latest_rows))
    )
    return BusinessCase(
        data_label=DATA_LABEL,
        hourly_rate_usd=HOURLY_RATE_USD,
        annual_platform_cost_usd=ANNUAL_PLATFORM_COST_USD,
        implementation_cost_usd=IMPLEMENTATION_COST_USD,
        go_live_date=GO_LIVE_DATE,
        tickets_deflected=sum(row.tickets_deflected for row in after),
        hours_saved=_money(hours_saved),
        months_after=months_after,
        labor_value_usd=_money(labor_raw),
        platform_cost_in_window_usd=_money(platform_raw),
        investment_usd=_money(investment_raw),
        net_value_usd=_money(net_raw),
        roi_pct=_tenths(net_raw / investment_raw * Decimal(100)),
        payback_months=_tenths(IMPLEMENTATION_COST_USD / monthly_net),
        avg_cost_before_usd=_weighted_cost(before),
        avg_cost_after_usd=_weighted_cost(after),
        adoption_pct=adoption,
    )


def adoption_by_team(
    rows: tuple[MonthlyRow, ...] | None = None,
) -> tuple[dict[str, Any], ...]:
    """Latest-month adoption for each sample team."""
    source = build_rows() if rows is None else rows
    latest = max(row.period_month for row in source)
    latest_rows = sorted(
        (row for row in source if row.period_month == latest),
        key=lambda row: row.team,
    )
    payload = []
    for row in latest_rows:
        adoption = _tenths(
            Decimal(row.active_users) * Decimal(100) / Decimal(row.licensed_users)
        )
        payload.append(
            {
                "team": row.team,
                "period_month": row.period_month.isoformat(),
                "active_users": row.active_users,
                "licensed_users": row.licensed_users,
                "adoption_pct": str(adoption),
            }
        )
    return tuple(payload)


def cost_before_after(
    rows: tuple[MonthlyRow, ...] | None = None,
) -> tuple[dict[str, Any], ...]:
    """Volume-weighted cost per resolution by team and phase."""
    source = build_rows() if rows is None else rows
    results = []
    for team in TEAMS:
        team_rows = [row for row in source if row.team == team.name]
        before = [row for row in team_rows if row.phase == "before"]
        after = [row for row in team_rows if row.phase == "after"]
        hours_after = _money(sum((row.hours_saved for row in after), Decimal(0)))
        results.append(
            {
                "team": team.name,
                "cost_before_usd": str(_weighted_cost(before)),
                "cost_after_usd": str(_weighted_cost(after)),
                "tickets_deflected_after": sum(row.tickets_deflected for row in after),
                "hours_saved_after": str(hours_after),
            }
        )
    return tuple(results)


def narrative_payload(rows: tuple[MonthlyRow, ...] | None = None) -> dict[str, Any]:
    """JSON-ready facts the narrative prompt is allowed to use."""
    source = build_rows() if rows is None else rows
    case = business_case(source)
    minutes = {
        team.name: str(team.minutes_saved_per_deflected_ticket) for team in TEAMS
    }
    return {
        "data_label": case.data_label,
        "go_live_date": case.go_live_date.isoformat(),
        "window": {
            "before": "2025-01-01 through 2025-06-01",
            "after": "2025-07-01 through 2025-12-01",
        },
        "assumptions": {
            "hourly_rate_usd": str(case.hourly_rate_usd),
            "annual_platform_cost_usd": str(case.annual_platform_cost_usd),
            "implementation_cost_usd": str(case.implementation_cost_usd),
            "minutes_saved_per_deflected_ticket": minutes,
        },
        "kpis": {
            "tickets_deflected": case.tickets_deflected,
            "hours_saved": str(case.hours_saved),
            "months_after": case.months_after,
            "labor_value_usd": str(case.labor_value_usd),
            "platform_cost_in_window_usd": str(case.platform_cost_in_window_usd),
            "investment_usd": str(case.investment_usd),
            "net_value_usd": str(case.net_value_usd),
            "roi_pct": str(case.roi_pct),
            "payback_months": str(case.payback_months),
            "avg_cost_before_usd": str(case.avg_cost_before_usd),
            "avg_cost_after_usd": str(case.avg_cost_after_usd),
            "adoption_pct": str(case.adoption_pct),
        },
        "adoption_by_team": list(adoption_by_team(source)),
        "cost_per_resolution_by_team": list(cost_before_after(source)),
        "formulas": FORMULAS,
    }


_VIEW_SQL = """
CREATE VIEW v_business_case AS
WITH bounds AS (
    SELECT
        SUM(CASE WHEN phase = 'after' THEN tickets_deflected ELSE 0 END)
            AS tickets_deflected,
        SUM(CASE WHEN phase = 'after' THEN hours_saved ELSE 0 END) AS hours_saved,
        COUNT(DISTINCT CASE WHEN phase = 'after' THEN period_month END)
            AS months_after,
        SUM(
            CASE
                WHEN phase = 'before' THEN cost_per_resolution_usd
                    * (tickets_deflected + tickets_resolved_by_human)
                ELSE 0
            END
        ) / NULLIF(
            SUM(
                CASE
                    WHEN phase = 'before'
                        THEN tickets_deflected + tickets_resolved_by_human
                    ELSE 0
                END
            ),
            0
        ) AS avg_cost_before_usd,
        SUM(
            CASE
                WHEN phase = 'after' THEN cost_per_resolution_usd
                    * (tickets_deflected + tickets_resolved_by_human)
                ELSE 0
            END
        ) / NULLIF(
            SUM(
                CASE
                    WHEN phase = 'after'
                        THEN tickets_deflected + tickets_resolved_by_human
                    ELSE 0
                END
            ),
            0
        ) AS avg_cost_after_usd
    FROM agent_monthly_outcomes
),
latest AS (
    SELECT
        SUM(active_users) AS active_users,
        SUM(licensed_users) AS licensed_users
    FROM agent_monthly_outcomes
    WHERE period_month = (SELECT MAX(period_month) FROM agent_monthly_outcomes)
)
SELECT
    assumptions.data_label,
    assumptions.hourly_rate_usd,
    assumptions.annual_platform_cost_usd,
    assumptions.implementation_cost_usd,
    assumptions.go_live_date,
    bounds.tickets_deflected,
    bounds.hours_saved,
    bounds.months_after,
    ROUND(bounds.hours_saved * assumptions.hourly_rate_usd, 2) AS labor_value_usd,
    ROUND(
        assumptions.annual_platform_cost_usd * bounds.months_after / 12, 2
    ) AS platform_cost_in_window_usd,
    ROUND(
        assumptions.implementation_cost_usd
        + (assumptions.annual_platform_cost_usd * bounds.months_after / 12),
        2
    ) AS investment_usd,
    ROUND(
        (bounds.hours_saved * assumptions.hourly_rate_usd)
        - (
            assumptions.implementation_cost_usd
            + (assumptions.annual_platform_cost_usd * bounds.months_after / 12)
        ),
        2
    ) AS net_value_usd,
    ROUND(
        (
            (bounds.hours_saved * assumptions.hourly_rate_usd)
            - (
                assumptions.implementation_cost_usd
                + (assumptions.annual_platform_cost_usd * bounds.months_after / 12)
            )
        ) / NULLIF(
            assumptions.implementation_cost_usd
            + (assumptions.annual_platform_cost_usd * bounds.months_after / 12),
            0
        ) * 100,
        1
    ) AS roi_pct,
    ROUND(
        assumptions.implementation_cost_usd / NULLIF(
            (bounds.hours_saved * assumptions.hourly_rate_usd / bounds.months_after)
            - (assumptions.annual_platform_cost_usd / 12),
            0
        ),
        1
    ) AS payback_months,
    ROUND(bounds.avg_cost_before_usd, 2) AS avg_cost_before_usd,
    ROUND(bounds.avg_cost_after_usd, 2) AS avg_cost_after_usd,
    ROUND(
        latest.active_users * 100.00 / NULLIF(latest.licensed_users, 0), 1
    ) AS adoption_pct
FROM bounds
CROSS JOIN latest
CROSS JOIN program_assumptions AS assumptions;

CREATE VIEW v_monthly_savings AS
SELECT
    outcomes.period_month,
    outcomes.phase,
    SUM(outcomes.tickets_deflected) AS tickets_deflected,
    SUM(outcomes.hours_saved) AS hours_saved,
    ROUND(SUM(outcomes.hours_saved) * assumptions.hourly_rate_usd, 2)
        AS labor_value_usd,
    outcomes.data_label
FROM agent_monthly_outcomes AS outcomes
CROSS JOIN program_assumptions AS assumptions
GROUP BY
    outcomes.period_month,
    outcomes.phase,
    outcomes.data_label,
    assumptions.hourly_rate_usd;

CREATE VIEW v_adoption_by_team AS
SELECT
    team,
    period_month,
    active_users,
    licensed_users,
    ROUND(active_users * 100.00 / licensed_users, 1) AS adoption_pct,
    data_label
FROM agent_monthly_outcomes
WHERE period_month = (SELECT MAX(period_month) FROM agent_monthly_outcomes);

CREATE VIEW v_cost_by_team_phase AS
SELECT
    team,
    phase,
    SUM(tickets_deflected) AS tickets_deflected,
    SUM(tickets_resolved_by_human) AS tickets_resolved_by_human,
    SUM(hours_saved) AS hours_saved,
    ROUND(
        SUM(
            cost_per_resolution_usd
            * (tickets_deflected + tickets_resolved_by_human)
        ) / NULLIF(SUM(tickets_deflected + tickets_resolved_by_human), 0),
        2
    ) AS avg_cost_per_resolution_usd,
    MAX(data_label) AS data_label
FROM agent_monthly_outcomes
GROUP BY team, phase;

CREATE VIEW v_cost_before_after AS
SELECT
    team,
    MAX(
        CASE WHEN phase = 'before' THEN avg_cost_per_resolution_usd END
    ) AS cost_before_usd,
    MAX(
        CASE WHEN phase = 'after' THEN avg_cost_per_resolution_usd END
    ) AS cost_after_usd,
    MAX(data_label) AS data_label
FROM v_cost_by_team_phase
GROUP BY team;
"""


def render_sql() -> str:
    """Render the Postgres seed, including views the dashboard and narrative share."""
    inserts = []
    for row in build_rows():
        inserts.append(
            "INSERT INTO agent_monthly_outcomes ("
            "period_month, team, phase, tickets_opened, tickets_deflected, "
            "tickets_resolved_by_human, hours_saved, cost_per_resolution_usd, "
            "active_users, licensed_users, data_label) VALUES ("
            f"'{row.period_month.isoformat()}', {_sql_string(row.team)}, "
            f"{_sql_string(row.phase)}, {row.tickets_opened}, "
            f"{row.tickets_deflected}, {row.tickets_resolved_by_human}, "
            f"{row.hours_saved}, {row.cost_per_resolution_usd}, "
            f"{row.active_users}, {row.licensed_users}, "
            f"{_sql_string(row.data_label)});"
        )
    header = (
        "-- Synthetic AI-agent deployment dataset.\n"
        f"-- {DATA_LABEL}\n"
        "-- Generated by ai_deployment_roi/metrics.py. Do not treat the figures as\n"
        "-- a customer result. Regenerate this file with build_assets.py.\n"
    )
    assumptions = (
        "CREATE TABLE program_assumptions (\n"
        "    id integer PRIMARY KEY,\n"
        "    data_label text NOT NULL,\n"
        "    hourly_rate_usd numeric(12, 2) NOT NULL,\n"
        "    annual_platform_cost_usd numeric(12, 2) NOT NULL,\n"
        "    implementation_cost_usd numeric(12, 2) NOT NULL,\n"
        "    go_live_date date NOT NULL\n"
        ");\n\n"
        "INSERT INTO program_assumptions (\n"
        "    id, data_label, hourly_rate_usd, annual_platform_cost_usd,\n"
        "    implementation_cost_usd, go_live_date\n"
        ") VALUES (\n"
        f"    1, {_sql_string(DATA_LABEL)}, {HOURLY_RATE_USD}, "
        f"{ANNUAL_PLATFORM_COST_USD},\n"
        f"    {IMPLEMENTATION_COST_USD}, '{GO_LIVE_DATE.isoformat()}'\n"
        ");\n"
    )
    table = """
CREATE TABLE agent_monthly_outcomes (
    period_month date NOT NULL,
    team text NOT NULL,
    phase text NOT NULL CHECK (phase IN ('before', 'after')),
    tickets_opened integer NOT NULL,
    tickets_deflected integer NOT NULL,
    tickets_resolved_by_human integer NOT NULL,
    hours_saved numeric(12, 2) NOT NULL,
    cost_per_resolution_usd numeric(12, 2) NOT NULL,
    active_users integer NOT NULL,
    licensed_users integer NOT NULL,
    data_label text NOT NULL,
    PRIMARY KEY (period_month, team),
    CHECK (tickets_deflected >= 0),
    CHECK (tickets_resolved_by_human >= 0),
    CHECK (tickets_deflected + tickets_resolved_by_human = tickets_opened),
    CHECK (active_users <= licensed_users)
);
"""
    return (
        header
        + "\n"
        + assumptions
        + table
        + "\n"
        + "\n".join(inserts)
        + "\n"
        + _VIEW_SQL
    )
