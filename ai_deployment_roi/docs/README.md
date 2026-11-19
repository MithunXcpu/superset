# AI Deployment ROI dashboard notes

This demo is a sample business-case pack. The numbers are generated. The
dashboard banner and every fact-table row use the label
`SYNTHETIC DEMO — not a real customer or deployment`.

## Charts

The imported dashboard has eight charts:

1. Tickets deflected after go-live
2. Hours saved after go-live
3. Sample ROI percent
4. Sample payback in months
5. Hours saved by month, split into before and after
6. Adoption by team in the latest month (December 2025)
7. Cost per resolution, before versus after, by team
8. A table of team totals by phase

## How a row is built

Each team has a steady opened-ticket volume. Before go-live, deflection and
hours saved stay small. After go-live, deflected tickets ramp across six
months with factors 0.70, 0.85, 1.00, 1.00, 1.05, and 1.08. Hours saved in the
after window are those deflected tickets times the team's assumed minutes,
divided by 60. Cost per resolution moves from the before rate toward the after
rate over the same ramp, and stops at the after rate once the factor reaches
1. Active users ramp the same way and never exceed licensed users.

## Screenshots

This folder does not ship a captured screenshot. After `docker compose up`,
open the dashboard and save a picture here if you want one in a later change.
The offline narrative is text, so run `python narrative.py --offline` to read
the one-page summary without the UI.
