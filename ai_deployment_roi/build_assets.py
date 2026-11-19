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
"""Write the SQL seed and the Superset dashboard export from the Python source."""

from __future__ import annotations

from pathlib import Path

from bundle import write_bundle
from metrics import render_sql

ROOT = Path(__file__).resolve().parent


def main() -> None:
    """Regenerate sql/ and dashboard_export/."""
    sql_path = ROOT / "sql" / "01_synthetic_ai_roi.sql"
    sql_path.parent.mkdir(parents=True, exist_ok=True)
    sql_path.write_text(render_sql(), encoding="utf-8")
    write_bundle(ROOT / "dashboard_export")
    print(f"Wrote {sql_path}")
    print(f"Wrote {ROOT / 'dashboard_export'}")


if __name__ == "__main__":
    main()
