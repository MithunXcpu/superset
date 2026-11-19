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
"""Checks that the dashboard export is a consistent Superset v1 bundle."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bundle import (  # noqa: E402
    bundle_files,
    DASHBOARD_TITLE,
    dump_yaml,
    SQLALCHEMY_URI,
)
from metrics import DATA_LABEL  # noqa: E402


def test_committed_export_matches_the_builder() -> None:
    """Re-running the builder does not change the committed YAML."""
    root = Path(__file__).resolve().parents[1] / "dashboard_export"
    for relative_path, document in bundle_files().items():
        found = (root / relative_path).read_text(encoding="utf-8")
        assert found == dump_yaml(document)


def test_bundle_links_dashboard_charts_datasets_and_database() -> None:
    """Chart UUIDs, dataset UUIDs, and the database UUID agree."""
    files = bundle_files()
    assert files["metadata.yaml"]["version"] == "1.0.0"
    assert files["metadata.yaml"]["type"] == "Dashboard"
    database = files["databases/AI_ROI_Synthetic_Postgres.yaml"]
    assert database["sqlalchemy_uri"] == SQLALCHEMY_URI
    assert database["allow_dml"] is False
    datasets = {
        document["uuid"]: document
        for path, document in files.items()
        if path.startswith("datasets/")
    }
    charts = {
        document["uuid"]: document
        for path, document in files.items()
        if path.startswith("charts/")
    }
    dashboard = files["dashboards/AI_Deployment_ROI.yaml"]
    assert dashboard["dashboard_title"] == DASHBOARD_TITLE
    assert DATA_LABEL in dashboard["description"]
    layout_uuids = {
        node["meta"]["uuid"]
        for node in dashboard["position"].values()
        if isinstance(node, dict) and node.get("type") == "CHART"
    }
    assert layout_uuids == set(charts)
    for chart in charts.values():
        assert chart["dataset_uuid"] in datasets
        assert chart["version"] == "1.0.0"
        assert "dataset_uuid" in chart
        assert "datasource_ref" not in chart
        assert "uuid" not in chart["params"]
    for dataset in datasets.values():
        assert dataset["database_uuid"] == database["uuid"]
        assert dataset["schema"] == "public"
        for metric in dataset["metrics"]:
            assert "uuid" not in metric
    widths = {"ROW-kpis": 0, "ROW-trend": 0, "ROW-cost": 0}
    for node in dashboard["position"].values():
        if not isinstance(node, dict) or node.get("type") != "CHART":
            continue
        row_id = node["parents"][-1]
        widths[row_id] += node["meta"]["width"]
    assert widths == {"ROW-kpis": 12, "ROW-trend": 12, "ROW-cost": 12}


def test_export_mentions_the_synthetic_banner() -> None:
    """The dashboard markdown states that the data is synthetic."""
    path = (
        Path(__file__).resolve().parents[1]
        / "dashboard_export"
        / "dashboards"
        / "AI_Deployment_ROI.yaml"
    )
    dashboard = yaml.safe_load(path.read_text(encoding="utf-8"))
    banner = dashboard["position"]["MARKDOWN-banner"]["meta"]["code"]
    assert DATA_LABEL in banner
