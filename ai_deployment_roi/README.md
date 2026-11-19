# AI Deployment ROI & Business Case

A local, docker-compose demo for people who build the ROI page behind an AI
agent rollout: value engineers, AI deployment or adoption leads, and customer
success managers. It loads a clearly labeled synthetic Postgres dataset, imports
a Superset dashboard (adoption, hours saved, cost per resolution, payback, ROI),
and drafts a one-page executive summary from those same figures.

The figures are sample data. They are not a customer result, a benchmark, or a
quote. The seed is marked `SYNTHETIC DEMO — not a real customer or deployment`
on every row and on the dashboard.

Superset itself is unchanged. This folder is the add-on: a compose file, a SQL
seed, a dashboard export, and a small Python narrative script.

## What the sample shows

Go-live in the seed is 1 July 2025. January–June are the baseline. July–December
are the value window. Teams are Support L1, Support L2, IT Helpdesk, Sales Ops,
and Finance Ops.

Assumptions stored in `program_assumptions`:

| Assumption | Sample value |
| --- | --- |
| Fully loaded hourly rate | $85 |
| Annual platform cost | $180,000 |
| One-time implementation | $75,000 |
| Minutes saved per deflected ticket | 15 (Support L1), 20 (Support L2), 18 (IT Helpdesk), 25 (Sales Ops), 30 (Finance Ops) |

Headline figures the seed produces for the six months after go-live:

| Figure | Sample value |
| --- | --- |
| Tickets deflected | 15,734 |
| Hours saved | 4,559.38 |
| Labor value | $387,547.30 |
| Investment (implementation + half the annual platform cost) | $165,000.00 |
| Net value | $222,547.30 |
| ROI | 134.9% |
| Payback of the implementation | 1.5 months |
| Weighted cost per resolution | $30.10 before, $15.40 after |
| Adoption in December 2025 | 83.1% |

Formulas, shared by the SQL views and `metrics.py`:

- Labor value = hours saved after go-live × hourly rate
- Investment = implementation + annual platform cost × 6/12
- ROI = (labor value − investment) / investment × 100
- Payback (months) = implementation / (monthly labor value − monthly platform cost)
- Adoption = active users / licensed users in the latest month

Hours saved after go-live are deflected tickets times the minutes assumption
above, divided by 60. The first two months after go-live ramp up (70%, then
85%) before the steady state.

## Architecture

```text
sql/01_synthetic_ai_roi.sql
        │
        ▼
Postgres  ── views: v_business_case, v_monthly_savings,
        │            v_adoption_by_team, v_cost_before_after,
        │            v_cost_by_team_phase
        │
        ├── Superset (apache/superset:6.1.0)
        │     database connection + imported dashboard export
        │
        └── narrative.py
              reads the same views (or metrics.py with --offline)
              └── NVIDIA OpenAI-compatible API
                    https://integrate.api.nvidia.com/v1
                    model meta/llama-3.3-70b-instruct
                    or the offline template when NVIDIA_API_KEY is unset
```

`LLM_PROVIDER=auto` uses NVIDIA when `NVIDIA_API_KEY` is set and the offline
template otherwise. A failed NVIDIA call falls back to that template unless
`LLM_FALLBACK=error`. The key is read from the environment. It is not committed.
`.env.example` has the placeholder.

## Run the dashboard

From this directory:

```bash
docker compose up
```

Wait until `http://localhost:8088/health` returns OK. The first start applies
Superset migrations and imports the dashboard. That takes a few minutes.

- Superset: http://localhost:8088
- Username / password: `admin` / `admin` (local demo only)
- Dashboard: **AI Deployment ROI & Business Case (Synthetic)**
- Direct path: http://localhost:8088/superset/dashboard/ai-deployment-roi-synthetic/
- Postgres for the narrative script: `localhost:5433`
  (`ai_roi` / `ai_roi_demo`, database `ai_roi`)

`docker compose down` removes the containers. The database has no named volume,
so the next `up` loads the seed again.

The published image is `apache/superset:6.1.0`. It is not a build of this fork.
The import bundle is the Superset v1 YAML format. Inside compose the connection
URI is `postgresql://ai_roi:ai_roi_demo@ai-roi-db:5432/ai_roi`. If you import
the zip somewhere else, edit that URI. Metric UUIDs are omitted because
Superset 6.1 treats them as an unknown field; the importer matches metrics by
name.

To import by hand, zip `dashboard_export/` under a single root folder (see
`bootstrap.sh`) and run:

```bash
superset import-dashboards -p ai_deployment_roi_dashboard.zip -u admin
```

## Run the narrative

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python narrative.py --offline
```

`--offline` does not need Postgres or an API key. It prints a one-page markdown
summary of the seed.

With the compose stack up, the script reads the views instead:

```bash
export AI_ROI_DATABASE_URL=postgresql://ai_roi:ai_roi_demo@localhost:5433/ai_roi
python narrative.py
```

To ask NVIDIA for the prose, set `NVIDIA_API_KEY` in an uncommitted env file
and export it. Do not commit the key.

```bash
export NVIDIA_API_KEY=your-key
export LLM_PROVIDER=auto
python narrative.py --offline
```

## Tests

```bash
pip install -r requirements.txt
python -m pytest tests
```

Regenerate the SQL and YAML after changing `metrics.py` or `bundle.py`:

```bash
python build_assets.py
```

## Layout

| Path | Role |
| --- | --- |
| `docker-compose.yml` | Postgres 16 and Superset 6.1.0 |
| `sql/01_synthetic_ai_roi.sql` | Synthetic tables and views |
| `dashboard_export/` | Superset v1 dashboard bundle |
| `bootstrap.sh` | Migrations, admin user, import, then gunicorn |
| `metrics.py` | Seed and formulas |
| `narrative.py` | One-page summary CLI |
| `llm_client.py` | NVIDIA client and offline template |
| `docs/README.md` | Chart list and how the rows are built |
