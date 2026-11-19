#!/usr/bin/env bash
#
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
#
# Initialize Superset, import the synthetic ROI dashboard, then serve it.
set -euo pipefail

superset db upgrade

superset fab create-admin \
    --username "${ADMIN_USERNAME:-admin}" \
    --firstname Superset \
    --lastname Admin \
    --email "${ADMIN_EMAIL:-admin@localhost}" \
    --password "${ADMIN_PASSWORD:-admin}" \
    || echo "Admin user already exists; continuing."

superset init

python - <<'PY'
import zipfile
from pathlib import Path

root = Path("/bootstrap/dashboard_export")
destination = Path("/tmp/ai_deployment_roi_dashboard.zip")
with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".yaml", ".yml"}:
            continue
        if path.name.startswith("."):
            continue
        archive.write(
            path,
            Path("ai_deployment_roi_dashboard") / path.relative_to(root),
        )
print(f"Wrote {destination}")
PY

superset import-dashboards \
    -p /tmp/ai_deployment_roi_dashboard.zip \
    -u "${ADMIN_USERNAME:-admin}"

exec /app/docker/entrypoints/run-server.sh
