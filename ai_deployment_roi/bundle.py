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
"""Build the Superset dashboard import bundle for the synthetic ROI demo."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from metrics import DATA_LABEL

DB_UUID = "11111111-1111-4111-8111-111111111111"
DATASET_CASE = "22222222-2222-4222-8222-222222222201"
DATASET_MONTHLY = "22222222-2222-4222-8222-222222222202"
DATASET_ADOPTION = "22222222-2222-4222-8222-222222222203"
DATASET_COST = "22222222-2222-4222-8222-222222222204"
DATASET_DETAIL = "22222222-2222-4222-8222-222222222205"
CHART_TICKETS = "33333333-3333-4333-8333-333333333301"
CHART_HOURS = "33333333-3333-4333-8333-333333333302"
CHART_ROI = "33333333-3333-4333-8333-333333333303"
CHART_PAYBACK = "33333333-3333-4333-8333-333333333304"
CHART_MONTHLY = "33333333-3333-4333-8333-333333333305"
CHART_ADOPTION = "33333333-3333-4333-8333-333333333306"
CHART_COST = "33333333-3333-4333-8333-333333333307"
CHART_TABLE = "33333333-3333-4333-8333-333333333308"
DASHBOARD_UUID = "44444444-4444-4444-8444-444444444444"

SQLALCHEMY_URI = "postgresql://ai_roi:ai_roi_demo@ai-roi-db:5432/ai_roi"
DASHBOARD_TITLE = "AI Deployment ROI & Business Case (Synthetic)"

YAML_HEADER = """# Licensed to the Apache Software Foundation (ASF) under one
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
"""

MARKDOWN = f"""**{DATA_LABEL}**

Sample pack for an AI-agent rollout business case. Go-live in the seed is
2025-07-01. Labor value uses the $85 hourly rate in `program_assumptions`.
Hours saved after go-live are deflected tickets times an assumed handle-time
(15–30 minutes, depending on the team). ROI and payback use the formulas in
`ai_deployment_roi/README.md`. Replace the seed before using this with a customer.
"""


def _column(
    name: str,
    type_name: str,
    *,
    is_dttm: bool = False,
    description: str | None = None,
) -> dict[str, Any]:
    """One physical column in a dataset export."""
    return {
        "advanced_data_type": None,
        "column_name": name,
        "description": description,
        "expression": None,
        "extra": None,
        "filterable": True,
        "groupby": True,
        "is_active": True,
        "is_dttm": is_dttm,
        "python_date_format": None,
        "type": type_name,
        "verbose_name": None,
    }


def _metric(
    name: str,
    expression: str,
    *,
    d3format: str | None = None,
) -> dict[str, Any]:
    """One saved metric.

    Metric UUIDs are omitted. Superset 6.1 rejects them as an unknown field,
    and the importer matches metrics by name.
    """
    return {
        "currency": None,
        "d3format": d3format,
        "description": None,
        "expression": expression,
        "extra": None,
        "metric_name": name,
        "metric_type": None,
        "verbose_name": name,
        "warning_text": None,
    }


def _dataset(
    uuid: str,
    table_name: str,
    description: str,
    columns: list[dict[str, Any]],
    metrics: list[dict[str, Any]],
    *,
    main_dttm_col: str | None = None,
) -> dict[str, Any]:
    """Dataset export pointing at a Postgres view."""
    return {
        "always_filter_main_dttm": False,
        "cache_timeout": None,
        "catalog": None,
        "columns": columns,
        "database_uuid": DB_UUID,
        "description": description,
        "extra": None,
        "filter_select_enabled": True,
        "main_dttm_col": main_dttm_col,
        "metrics": metrics,
        "normalize_columns": False,
        "offset": 0,
        "schema": "public",
        "sql": None,
        "table_name": table_name,
        "template_params": None,
        "uuid": uuid,
        "version": "1.0.0",
    }


def _query_context(
    form_data: dict[str, Any],
    columns: list[str],
    metrics: list[str],
) -> str:
    """Stored query context so `GET /api/v1/chart/<id>/data/` can run the chart."""
    return json.dumps(
        {
            "datasource": {"id": 1, "type": "table"},
            "force": False,
            "queries": [
                {
                    "filters": [],
                    "extras": {"having": "", "where": ""},
                    "applied_time_extras": {},
                    "columns": columns,
                    "metrics": metrics,
                    "annotation_layers": [],
                    "row_limit": 1000,
                    "series_limit": 0,
                    "order_desc": True,
                    "time_range": "No filter",
                    "url_params": {},
                    "custom_params": {},
                    "custom_form_data": {},
                }
            ],
            "form_data": form_data,
            "result_format": "json",
            "result_type": "full",
        }
    )


def _chart(
    uuid: str,
    dataset_uuid: str,
    slice_name: str,
    viz_type: str,
    params: dict[str, Any],
    columns: list[str],
    metrics: list[str],
) -> dict[str, Any]:
    """Chart export. Datasource ids are placeholders rewritten on import."""
    form_data = {"datasource": "1__table", "viz_type": viz_type, **params}
    return {
        "cache_timeout": None,
        "certification_details": None,
        "certified_by": None,
        "dataset_uuid": dataset_uuid,
        "description": DATA_LABEL,
        "params": form_data,
        "query_context": _query_context(form_data, columns, metrics),
        "slice_name": slice_name,
        "uuid": uuid,
        "version": "1.0.0",
        "viz_type": viz_type,
    }


def _big_number(
    uuid: str,
    slice_name: str,
    metric: str,
    y_format: str,
    subheader: str,
) -> dict[str, Any]:
    """A single-value chart on the one-row business-case view."""
    return _chart(
        uuid,
        DATASET_CASE,
        slice_name,
        "big_number_total",
        {
            "metric": metric,
            "adhoc_filters": [],
            "header_font_size": 0.4,
            "subheader_font_size": 0.15,
            "y_axis_format": y_format,
            "subheader": subheader,
            "time_range": "No filter",
        },
        [],
        [metric],
    )


def _bar(
    uuid: str,
    dataset_uuid: str,
    slice_name: str,
    x_axis: str,
    metrics: list[str],
    groupby: list[str],
    y_format: str,
    *,
    time_grain: str | None = None,
) -> dict[str, Any]:
    """A bar chart. `time_grain` is set only when the x-axis is a month."""
    params: dict[str, Any] = {
        "x_axis": x_axis,
        "metrics": metrics,
        "groupby": groupby,
        "adhoc_filters": [],
        "row_limit": 1000,
        "truncate_metric": True,
        "show_legend": True,
        "rich_tooltip": True,
        "y_axis_format": y_format,
        "color_scheme": "supersetColors",
        "time_range": "No filter",
        "annotation_layers": [],
    }
    if time_grain:
        params["time_grain_sqla"] = time_grain
    return _chart(
        uuid,
        dataset_uuid,
        slice_name,
        "echarts_timeseries_bar",
        params,
        [x_axis, *groupby],
        metrics,
    )


def datasets() -> dict[str, dict[str, Any]]:
    """Dataset exports keyed by relative zip path."""
    label = DATA_LABEL
    case_columns = [
        _column("data_label", "TEXT", description=label),
        _column("hourly_rate_usd", "NUMERIC"),
        _column("annual_platform_cost_usd", "NUMERIC"),
        _column("implementation_cost_usd", "NUMERIC"),
        _column("go_live_date", "DATE"),
        _column("tickets_deflected", "BIGINT"),
        _column("hours_saved", "NUMERIC"),
        _column("months_after", "BIGINT"),
        _column("labor_value_usd", "NUMERIC"),
        _column("platform_cost_in_window_usd", "NUMERIC"),
        _column("investment_usd", "NUMERIC"),
        _column("net_value_usd", "NUMERIC"),
        _column("roi_pct", "NUMERIC"),
        _column("payback_months", "NUMERIC"),
        _column("avg_cost_before_usd", "NUMERIC"),
        _column("avg_cost_after_usd", "NUMERIC"),
        _column("adoption_pct", "NUMERIC"),
    ]
    return {
        "datasets/AI_ROI_Synthetic_Postgres/v_business_case.yaml": _dataset(
            DATASET_CASE,
            "v_business_case",
            f"One-row sample business case. {label}",
            case_columns,
            [
                _metric("tickets_deflected", "SUM(tickets_deflected)", d3format=",.0f"),
                _metric("hours_saved", "SUM(hours_saved)", d3format=",.0f"),
                _metric("roi_pct", "MAX(roi_pct)", d3format=",.1f"),
                _metric("payback_months", "MAX(payback_months)", d3format=",.1f"),
            ],
        ),
        "datasets/AI_ROI_Synthetic_Postgres/v_monthly_savings.yaml": _dataset(
            DATASET_MONTHLY,
            "v_monthly_savings",
            f"Monthly hours and labor value by phase. {label}",
            [
                _column("period_month", "DATE", is_dttm=True),
                _column("phase", "TEXT"),
                _column("tickets_deflected", "BIGINT"),
                _column("hours_saved", "NUMERIC"),
                _column("labor_value_usd", "NUMERIC"),
                _column("data_label", "TEXT", description=label),
            ],
            [_metric("hours_saved", "SUM(hours_saved)", d3format=",.0f")],
            main_dttm_col="period_month",
        ),
        "datasets/AI_ROI_Synthetic_Postgres/v_adoption_by_team.yaml": _dataset(
            DATASET_ADOPTION,
            "v_adoption_by_team",
            f"Latest-month active users over licensed users. {label}",
            [
                _column("team", "TEXT"),
                _column("period_month", "DATE"),
                _column("active_users", "BIGINT"),
                _column("licensed_users", "BIGINT"),
                _column("adoption_pct", "NUMERIC"),
                _column("data_label", "TEXT", description=label),
            ],
            [_metric("adoption_pct", "MAX(adoption_pct)", d3format=",.1f")],
        ),
        "datasets/AI_ROI_Synthetic_Postgres/v_cost_before_after.yaml": _dataset(
            DATASET_COST,
            "v_cost_before_after",
            f"Volume-weighted cost per resolution by team. {label}",
            [
                _column("team", "TEXT"),
                _column("cost_before_usd", "NUMERIC"),
                _column("cost_after_usd", "NUMERIC"),
                _column("data_label", "TEXT", description=label),
            ],
            [
                _metric("cost_before_usd", "MAX(cost_before_usd)", d3format="$,.2f"),
                _metric("cost_after_usd", "MAX(cost_after_usd)", d3format="$,.2f"),
            ],
        ),
        "datasets/AI_ROI_Synthetic_Postgres/v_cost_by_team_phase.yaml": _dataset(
            DATASET_DETAIL,
            "v_cost_by_team_phase",
            f"Team totals for the before and after windows. {label}",
            [
                _column("team", "TEXT"),
                _column("phase", "TEXT"),
                _column("tickets_deflected", "BIGINT"),
                _column("tickets_resolved_by_human", "BIGINT"),
                _column("hours_saved", "NUMERIC"),
                _column("avg_cost_per_resolution_usd", "NUMERIC"),
                _column("data_label", "TEXT", description=label),
            ],
            [_metric("count", "COUNT(*)")],
        ),
    }


def charts() -> dict[str, dict[str, Any]]:
    """Chart exports keyed by relative zip path."""
    table_columns = [
        "team",
        "phase",
        "tickets_deflected",
        "hours_saved",
        "avg_cost_per_resolution_usd",
        "data_label",
    ]
    return {
        "charts/Tickets_deflected.yaml": _big_number(
            CHART_TICKETS,
            "Tickets deflected (after go-live)",
            "tickets_deflected",
            ",.0f",
            "sample, six months after go-live",
        ),
        "charts/Hours_saved.yaml": _big_number(
            CHART_HOURS,
            "Hours saved (after go-live)",
            "hours_saved",
            ",.0f",
            "sample handle time avoided",
        ),
        "charts/ROI_percent.yaml": _big_number(
            CHART_ROI,
            "Sample ROI %",
            "roi_pct",
            ",.1f",
            "net value / investment, percent",
        ),
        "charts/Payback_months.yaml": _big_number(
            CHART_PAYBACK,
            "Sample payback (months)",
            "payback_months",
            ",.1f",
            "implementation / monthly net",
        ),
        "charts/Hours_saved_by_month.yaml": _bar(
            CHART_MONTHLY,
            DATASET_MONTHLY,
            "Hours saved by month",
            "period_month",
            ["hours_saved"],
            ["phase"],
            ",.0f",
            time_grain="P1M",
        ),
        "charts/Adoption_by_team.yaml": _bar(
            CHART_ADOPTION,
            DATASET_ADOPTION,
            "Adoption by team (latest month)",
            "team",
            ["adoption_pct"],
            [],
            ",.1f",
        ),
        "charts/Cost_per_resolution.yaml": _bar(
            CHART_COST,
            DATASET_COST,
            "Cost per resolution, before vs after",
            "team",
            ["cost_before_usd", "cost_after_usd"],
            [],
            "$,.2f",
        ),
        "charts/Team_totals_by_phase.yaml": _chart(
            CHART_TABLE,
            DATASET_DETAIL,
            "Team totals by phase",
            "table",
            {
                "query_mode": "raw",
                "all_columns": table_columns,
                "percent_metrics": [],
                "adhoc_filters": [],
                "order_by_cols": [],
                "row_limit": 100,
                "server_pagination": False,
                "include_search": True,
                "page_length": 20,
                "time_range": "No filter",
            },
            table_columns,
            [],
        ),
    }


def _node(
    node_id: str,
    node_type: str,
    *,
    children: list[str] | None = None,
    meta: dict[str, Any] | None = None,
    parents: list[str] | None = None,
) -> dict[str, Any]:
    """One dashboard layout node."""
    node: dict[str, Any] = {"id": node_id, "type": node_type}
    if children is not None:
        node["children"] = children
    if meta is not None:
        node["meta"] = meta
    if parents is not None:
        node["parents"] = parents
    return node


def dashboard() -> dict[str, Any]:
    """Dashboard export whose chart nodes reference the chart UUIDs."""
    charts_meta = (
        ("CHART-tickets", 301, CHART_TICKETS, "Tickets deflected (after go-live)", 3),
        ("CHART-hours", 302, CHART_HOURS, "Hours saved (after go-live)", 3),
        ("CHART-roi", 303, CHART_ROI, "Sample ROI %", 3),
        ("CHART-payback", 304, CHART_PAYBACK, "Sample payback (months)", 3),
        ("CHART-monthly", 305, CHART_MONTHLY, "Hours saved by month", 7),
        ("CHART-adoption", 306, CHART_ADOPTION, "Adoption by team (latest month)", 5),
        ("CHART-cost", 307, CHART_COST, "Cost per resolution, before vs after", 7),
        ("CHART-table", 308, CHART_TABLE, "Team totals by phase", 5),
    )
    position: dict[str, Any] = {
        "DASHBOARD_VERSION_KEY": "v2",
        "ROOT_ID": _node("ROOT_ID", "ROOT", children=["GRID_ID"]),
        "GRID_ID": _node(
            "GRID_ID",
            "GRID",
            children=["ROW-banner", "ROW-kpis", "ROW-trend", "ROW-cost"],
            parents=["ROOT_ID"],
        ),
        "HEADER_ID": _node("HEADER_ID", "HEADER", meta={"text": DASHBOARD_TITLE}),
        "ROW-banner": _node(
            "ROW-banner",
            "ROW",
            children=["MARKDOWN-banner"],
            meta={"background": "BACKGROUND_TRANSPARENT"},
            parents=["ROOT_ID", "GRID_ID"],
        ),
        "MARKDOWN-banner": _node(
            "MARKDOWN-banner",
            "MARKDOWN",
            meta={"code": MARKDOWN, "height": 24, "width": 12},
            parents=["ROOT_ID", "GRID_ID", "ROW-banner"],
        ),
        "ROW-kpis": _node(
            "ROW-kpis",
            "ROW",
            children=["CHART-tickets", "CHART-hours", "CHART-roi", "CHART-payback"],
            meta={"background": "BACKGROUND_TRANSPARENT"},
            parents=["ROOT_ID", "GRID_ID"],
        ),
        "ROW-trend": _node(
            "ROW-trend",
            "ROW",
            children=["CHART-monthly", "CHART-adoption"],
            meta={"background": "BACKGROUND_TRANSPARENT"},
            parents=["ROOT_ID", "GRID_ID"],
        ),
        "ROW-cost": _node(
            "ROW-cost",
            "ROW",
            children=["CHART-cost", "CHART-table"],
            meta={"background": "BACKGROUND_TRANSPARENT"},
            parents=["ROOT_ID", "GRID_ID"],
        ),
    }
    row_for = {
        "CHART-tickets": "ROW-kpis",
        "CHART-hours": "ROW-kpis",
        "CHART-roi": "ROW-kpis",
        "CHART-payback": "ROW-kpis",
        "CHART-monthly": "ROW-trend",
        "CHART-adoption": "ROW-trend",
        "CHART-cost": "ROW-cost",
        "CHART-table": "ROW-cost",
    }
    height_for = {"ROW-kpis": 42, "ROW-trend": 50, "ROW-cost": 50}
    for node_id, chart_id, uuid, name, width in charts_meta:
        row_id = row_for[node_id]
        position[node_id] = _node(
            node_id,
            "CHART",
            children=[],
            meta={
                "chartId": chart_id,
                "height": height_for[row_id],
                "sliceName": name,
                "uuid": uuid,
                "width": width,
            },
            parents=["ROOT_ID", "GRID_ID", row_id],
        )
    return {
        "certification_details": None,
        "certified_by": None,
        "css": "",
        "dashboard_title": DASHBOARD_TITLE,
        "description": (
            f"{DATA_LABEL} Charts cover adoption, hours saved, cost per "
            "resolution, payback, and ROI for a sample AI-agent rollout."
        ),
        "metadata": {
            "timed_refresh_immune_slices": [],
            "expanded_slices": {},
            "refresh_frequency": 0,
            "color_scheme": "supersetColors",
            "cross_filters_enabled": False,
            "native_filter_configuration": [],
        },
        "position": position,
        "published": True,
        "slug": "ai-deployment-roi-synthetic",
        "uuid": DASHBOARD_UUID,
        "version": "1.0.0",
    }


def database() -> dict[str, Any]:
    """Database export for the compose-network Postgres."""
    return {
        "allow_csv_upload": False,
        "allow_ctas": False,
        "allow_cvas": False,
        "allow_dml": False,
        "allow_run_async": False,
        "cache_timeout": None,
        "database_name": "AI ROI Synthetic Postgres",
        "expose_in_sqllab": True,
        "extra": {"allows_virtual_table_explore": True},
        "sqlalchemy_uri": SQLALCHEMY_URI,
        "uuid": DB_UUID,
        "version": "1.0.0",
    }


def bundle_files() -> dict[str, dict[str, Any]]:
    """All YAML documents in the import bundle, without the root folder."""
    files: dict[str, dict[str, Any]] = {
        "metadata.yaml": {
            "version": "1.0.0",
            "type": "Dashboard",
            "timestamp": "2026-01-15T00:00:00+00:00",
        },
        "databases/AI_ROI_Synthetic_Postgres.yaml": database(),
    }
    files.update(datasets())
    files.update(charts())
    files["dashboards/AI_Deployment_ROI.yaml"] = dashboard()
    return files


def dump_yaml(document: dict[str, Any]) -> str:
    """Serialize one export document with the ASF header."""
    body = yaml.safe_dump(document, sort_keys=False, allow_unicode=True)
    return YAML_HEADER + body


def write_bundle(directory: Path) -> None:
    """Write the dashboard export tree."""
    for relative_path, document in bundle_files().items():
        path = directory / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(dump_yaml(document), encoding="utf-8")
