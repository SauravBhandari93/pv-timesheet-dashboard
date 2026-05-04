# PV Timesheet Dashboard — Supabase Migration Guide

> Full record of what we discussed, what we changed, and how the system works after migration from Flask to Supabase Edge Functions.

---

## Table of Contents

1. [Why We Migrated](#1-why-we-migrated)
2. [Architecture: Before vs After](#2-architecture-before-vs-after)
3. [What Changed — File by File](#3-what-changed--file-by-file)
4. [Complete Setup Steps (What We Did)](#4-complete-setup-steps-what-we-did)
5. [Supabase Database Schema](#5-supabase-database-schema)
6. [Edge Functions — What Each One Does](#6-edge-functions--what-each-one-does)
7. [Odoo XML-RPC Integration (Inside Edge Functions)](#7-odoo-xml-rpc-integration-inside-edge-functions)
8. [Frontend Changes](#8-frontend-changes)
9. [How Data Flows Now](#9-how-data-flows-now)
10. [Scheduled Sync Setup](#10-scheduled-sync-setup)
11. [Vercel Deployment](#11-vercel-deployment)
12. [How to Maintain Going Forward](#12-how-to-maintain-going-forward)
13. [Troubleshooting](#13-troubleshooting)

---

## 1. Why We Migrated

**Original problem with Flask backend:**
- Had to deploy and maintain a Python server (Render/Heroku)
- In-memory cache was per-worker — 2 Gunicorn workers meant 2 independent caches
- Every cache miss meant a slow Odoo XML-RPC call during a user's page load
- If Odoo was down, the dashboard was down

**What Supabase gives us:**
- Zero backend to deploy or maintain
- PostgreSQL database stores all timesheet data persistently
- Edge Functions run serverlessly — no server management
- Data stays in Supabase even if Odoo is temporarily down
- Auto-scales without any configuration
- Free tier is enough for this use case

---

## 2. Architecture: Before vs After

### Before (Flask)

```
User Browser
     ↓ (every page load / filter change)
Flask app.py  (Render/Heroku)
     ↓ (on cache miss, ~every 5 min)
Odoo XML-RPC
```

**Problems:**
- Flask process must always be running
- Cache resets on every deploy or restart
- Multiple workers = multiple independent caches

### After (Supabase)

```
User Browser
     ↓ (every filter change)
Supabase Edge Functions  (serverless, auto-hosted)
     ↓ (queries)
Supabase PostgreSQL  (persistent database)

Odoo XML-RPC
     ↓ (sync every 30 min via cron)
Supabase PostgreSQL
```

**Benefits:**
- No server to manage
- Data persists in PostgreSQL — survives restarts, deploys, scaling
- Edge Functions are globally distributed
- Frontend (Vercel) is fully static — no backend at all

---

## 3. What Changed — File by File

### New files created

| File | Purpose |
|---|---|
| `supabase/functions/_shared/odoo.ts` | Shared Odoo XML-RPC client (auth + search_read) |
| `supabase/functions/sync-odoo/index.ts` | Fetches all timesheets from Odoo, upserts into Supabase DB |
| `supabase/functions/get-aggregates/index.ts` | Replaces Flask `/api/aggregates` — main dashboard data |
| `supabase/functions/get-employee/index.ts` | Replaces Flask `/api/employee` — employee drill-down |
| `supabase/functions/get-project/index.ts` | Replaces Flask `/api/project` — project drill-down |
| `supabase/functions/get-staff-config/index.ts` | Replaces Flask `/api/staff-config` |
| `site/index.html` | Copy of `dashboard.html` with all Flask/Jinja2 removed |
| `site/PV_Logo.png` | Logo copied for static hosting |
| `supabase/config.toml` | Supabase CLI config (auto-generated) |
| `SUPABASE_MIGRATION.md` | This document |

### Modified files

| File | What changed |
|---|---|
| `templates/dashboard.html` | Removed all `url_for()` Jinja2 calls; added `const API = "..."` constant; replaced all `fetch('/api/...')` calls with Supabase URLs; removed `/api/timesheets` legacy fallback; removed `script.js` reference |

### Files that stay unchanged (still used)

| File | Status |
|---|---|
| `app.py` | Kept as reference — no longer needed to run |
| `staff_config.json` | Reference copy — live config is now in Supabase `staff_config` table |
| `public/PV_Logo.png` | Original logo file |
| `CLAUDE.md` | Development notes |

### Files no longer needed

| File | Why |
|---|---|
| `requirements.txt` | No Python server needed |
| `Procfile` | No Gunicorn needed |
| `runtime.txt` | No Python version needed |
| `static/script.js` | Legacy table loader — removed from dashboard |

---

## 4. Complete Setup Steps (What We Did)

### Phase 1 — Supabase Project

1. Created Supabase project at https://supabase.com → named `pv-timesheet`
2. Noted the **Reference ID**: `deppuufhjctbusypehvy`
3. Ran SQL to create `timesheets` and `staff_config` tables (see Section 5)
4. Seeded `staff_config` table with team configuration
5. Enabled RLS (Row Level Security) on both tables — edge functions use `service_role_key` which bypasses RLS, so this is safe and protects against direct public access

### Phase 2 — Supabase CLI

```bash
# Installed via Scoop (winget didn't work on this machine)
scoop bucket add supabase https://github.com/supabase/scoop-bucket.git
scoop install supabase

# Logged in
supabase login

# Initialized in project folder
supabase init

# Linked to the Supabase project
supabase link --project-ref deppuufhjctbusypehvy
```

### Phase 3 — Edge Functions Created

```bash
supabase functions new sync-odoo
supabase functions new get-aggregates
supabase functions new get-employee
supabase functions new get-project
supabase functions new get-staff-config
```

Then wrote code into each `index.ts` (replacing the default boilerplate).

**Note about VS Code errors:** VS Code shows red errors (`Cannot find name 'Deno'`) in these files because it uses the Node.js TypeScript checker by default. These are **not real errors** — the code runs correctly on Supabase. Fix by installing the `denoland.vscode-deno` extension in VS Code.

### Phase 4 — Set Odoo Credentials as Secrets

```bash
supabase secrets set ODOO_URL=https://pv-advisory.odoo.com
supabase secrets set ODOO_DB=pv-advisory
supabase secrets set ODOO_USERNAME=ankur.goyal@pvadvisory.in
supabase secrets set ODOO_API_KEY=<api_key>
```

`SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are injected automatically by the runtime.

### Phase 5 — Deploy Edge Functions

```bash
supabase functions deploy sync-odoo        --no-verify-jwt
supabase functions deploy get-aggregates   --no-verify-jwt
supabase functions deploy get-employee     --no-verify-jwt
supabase functions deploy get-project      --no-verify-jwt
supabase functions deploy get-staff-config --no-verify-jwt
```

`--no-verify-jwt` allows the frontend to call these functions without a Supabase auth token (matching the original no-login behavior).

**Docker warning is harmless** — Docker is only needed for local testing, not deployment.

### Phase 6 — First Sync (Odoo → Supabase)

```powershell
Invoke-WebRequest -Method POST -Uri "https://deppuufhjctbusypehvy.supabase.co/functions/v1/sync-odoo" -UseBasicParsing
```

Result: `{"synced": 7236, "at": "2026-04-27T07:31:11.101Z"}` — 7,236 records synced.

**Parser bug found and fixed:** The initial XML-RPC parser used regex-based nested matching which failed to correctly extract Many2one field tuples (e.g., `employee_id` was returning just the integer ID `5` instead of `[5, "Jyoti Batra"]`). Fixed by rewriting `_shared/odoo.ts` with a stack-based parser using a `findClose()` depth counter function.

After fix, redeployed and re-synced. Employee names now show correctly.

### Phase 7 — Scheduled Sync (Every 30 Minutes)

In Supabase SQL Editor:

```sql
CREATE EXTENSION IF NOT EXISTS pg_cron;
CREATE EXTENSION IF NOT EXISTS pg_net;

SELECT cron.schedule(
  'sync-odoo-30min',
  '*/30 * * * *',
  $$SELECT net.http_post(
      url := 'https://deppuufhjctbusypehvy.supabase.co/functions/v1/sync-odoo',
      headers := '{"Content-Type":"application/json"}'::jsonb
  )$$
);
```

### Phase 8 — Frontend Updated

Removed all Flask/Jinja2 dependencies from `dashboard.html`:
- `{{ url_for(...) }}` calls replaced with plain paths or inlined styles
- `fetch('/api/...')` calls replaced with Supabase function URLs
- Added `const API = "https://deppuufhjctbusypehvy.supabase.co/functions/v1"` constant
- Removed legacy `/api/timesheets` fallback
- Removed `<script src="{{ url_for('static', filename='script.js') }}">` tag
- Inlined the 3-line `style.css` reset directly into `<head>`

### Phase 9 — Static Site Prepared

```
site/
├── index.html    ← dashboard.html with all changes applied
└── PV_Logo.png   ← company logo
```

Tested locally:
```bash
cd site/
python -m http.server 3000
# Open http://localhost:3000
```

Frontend loaded and fetched live data from Supabase — confirmed working.

### Phase 10 — Vercel Deployment

1. Pushed code to GitHub (`SauravBhandari93/pv-timesheet-dashboard`)
2. Vercel → Import from Git → select repo
3. **Root Directory:** `site`
4. **Framework Preset:** Other
5. **Build Command:** empty
6. **Output Directory:** empty
7. Deploy → live URL assigned

---

## 5. Supabase Database Schema

```sql
-- Main data table (one row per Odoo timesheet entry)
CREATE TABLE timesheets (
  id          BIGINT PRIMARY KEY,   -- Odoo record ID (used for upsert deduplication)
  employee    TEXT   NOT NULL,      -- Employee display name
  hours       FLOAT  NOT NULL DEFAULT 0,
  description TEXT,                 -- Task description (Odoo 'name' field)
  date        DATE   NOT NULL,
  project     TEXT,                 -- Project display name
  task        TEXT,                 -- Task display name
  synced_at   TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for filter performance
CREATE INDEX idx_ts_date     ON timesheets(date);
CREATE INDEX idx_ts_employee ON timesheets(employee);
CREATE INDEX idx_ts_project  ON timesheets(project);

-- Staff configuration (single-row table)
CREATE TABLE staff_config (
  id         INT  PRIMARY KEY DEFAULT 1,
  config     JSONB NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Why upsert with Odoo ID as primary key?**
Every sync call uses `upsert({ onConflict: 'id' })` — if a record already exists (same Odoo ID), it updates it. If new, it inserts. This means syncs are safe to run as often as needed without creating duplicates.

---

## 6. Edge Functions — What Each One Does

All functions live in `supabase/functions/`. They are Deno/TypeScript serverless functions.

### `sync-odoo` — Odoo → Supabase sync

**URL:** `POST https://deppuufhjctbusypehvy.supabase.co/functions/v1/sync-odoo`

**What it does:**
1. Reads Odoo credentials from Supabase secrets
2. Authenticates with Odoo via XML-RPC → gets `uid`
3. Calls `search_read` on `account.analytic.line` → fetches ALL timesheet records
4. Maps Odoo field names to our DB column names
5. Upserts into `timesheets` table in batches of 1000

**Response:**
```json
{ "synced": 7236, "at": "2026-04-27T07:40:08.203Z" }
```

**When it runs:** Every 30 minutes via pg_cron, or manually via POST request.

---

### `get-aggregates` — Main dashboard data

**URL:** `GET https://deppuufhjctbusypehvy.supabase.co/functions/v1/get-aggregates`

**Query params:**

| Param | Values | Default |
|---|---|---|
| `period` | `ALL`, `3M`, `6M`, `MONTH` | `ALL` |
| `month` | `YYYY-MM` | null |
| `employee` | Employee name or `ALL` | `ALL` |
| `project` | Project name or `ALL` | `ALL` |
| `billable` | `true`, `false` | null (show all) |

**What it does:**
1. Loads `staff_config` from DB
2. Queries `timesheets` table with date/employee/project filters
3. Applies billability logic (keyword matching against `non_billable_tasks`)
4. Aggregates into KPIs, per-employee stats, per-project stats, flat task list
5. Returns JSON

**Billability logic:** An entry is non-billable if any keyword from `staff_config.non_billable_tasks` appears (case-insensitive substring) in the task name, description, or project name.

---

### `get-employee` — Employee drill-down

**URL:** `GET .../get-employee?name=<name>`

Returns total hours, billable hours, all tasks, and per-project breakdown for one employee. Called when user clicks a row in the Employees table.

---

### `get-project` — Project drill-down

**URL:** `GET .../get-project?name=<name>`

Returns total hours, all tasks, and per-employee breakdown for one project. Called when user clicks a row in the Projects table.

---

### `get-staff-config` — Team configuration

**URL:** `GET .../get-staff-config`

Returns the `staff_config.config` JSONB from Supabase DB. Used by the frontend on page load to know which employees are new/resigned.

---

## 7. Odoo XML-RPC Integration (Inside Edge Functions)

The `_shared/odoo.ts` file contains a custom Odoo XML-RPC client written in Deno/TypeScript. It does not use any npm package — it builds and parses XML manually.

### Why XML-RPC and not JSON-RPC?

Odoo supports both XML-RPC and JSON-RPC externally. We use XML-RPC because:
- API key authentication (`ODOO_API_KEY`) works reliably with XML-RPC in all Odoo versions
- JSON-RPC external access requires session cookies, which don't work with API keys
- `xmlrpc.client` is available in Python stdlib; our Deno implementation is self-contained

### Two-step authentication

```
Step 1: POST /xmlrpc/2/common → authenticate(db, username, api_key)
        Returns: uid (integer, e.g. 7)

Step 2: POST /xmlrpc/2/object → execute_kw(db, uid, api_key, model, method, args, kwargs)
        Returns: array of records
```

### Fields fetched from Odoo

Model: `account.analytic.line` (Odoo's timesheet entry model)

| Odoo field | Type | Stored as |
|---|---|---|
| `id` | Integer | `id` (primary key) |
| `employee_id` | Many2one `[id, name]` | `employee` (name only) |
| `unit_amount` | Float | `hours` |
| `name` | Char | `description` |
| `date` | Date | `date` |
| `project_id` | Many2one `[id, name]` | `project` (name only) |
| `task_id` | Many2one `[id, name]` | `task` (name only) |

### The parser bug we fixed

**Problem:** The original regex-based XML parser used non-greedy `[\s\S]*?` matching. For Many2one fields like `employee_id`, the Odoo XML-RPC response returns:
```xml
<value><array><data>
  <value><int>5</int></value>
  <value><string>Jyoti Batra</string></value>
</data></array></value>
```

The regex was incorrectly matching only the first inner `<value>` (the integer ID) instead of the full array. Result: employee names were stored as `"5"`, `"8"`, `"7"` (IDs) instead of actual names.

**Fix:** Rewrote the parser with a `findClose(xml, from, open, close)` function that uses a depth counter to correctly find the matching closing tag for any opening tag, regardless of nesting. This correctly extracts `[5, "Jyoti Batra"]` and stores `"Jyoti Batra"`.

---

## 8. Frontend Changes

The dashboard frontend (`templates/dashboard.html` / `site/index.html`) is a ~2300-line single-page app with all CSS and JavaScript inline. These specific changes were made:

### Removed Flask/Jinja2 dependencies

| Was | Replaced with |
|---|---|
| `{{ url_for('public_static', filename='PV_Logo.png') }}` | `./PV_Logo.png` |
| `{{ url_for('static', filename='style.css') }}` | Inlined 3-line CSS reset in `<head>` |
| `<script src="{{ url_for('static', filename='script.js') }}">` | Removed entirely |

### Added Supabase API base constant

Added as the very first line inside the main `<script>` block:

```javascript
const API = "https://deppuufhjctbusypehvy.supabase.co/functions/v1";
```

### Replaced all API fetch calls

| Old (Flask) | New (Supabase) |
|---|---|
| `fetch('/api/staff-config')` | `fetch(\`${API}/get-staff-config\`)` |
| `fetch('/api/aggregates')` | `fetch(\`${API}/get-aggregates\`)` |
| ``fetch(`/api/aggregates?${params}`)`` | ``fetch(`${API}/get-aggregates?${params}`)`` |
| ``fetch(`/api/employee?name=${name}`)`` | ``fetch(`${API}/get-employee?name=${name}`)`` |
| ``fetch(`/api/project?name=${name}`)`` | ``fetch(`${API}/get-project?name=${name}`)`` |
| `fetch('/api/timesheets')` | Removed (legacy fallback deleted) |

---

## 9. How Data Flows Now

```
┌─────────────────────────────────────────────────────────┐
│                    EVERY 30 MINUTES                     │
│                                                         │
│  pg_cron (Supabase)                                     │
│      → POST sync-odoo edge function                     │
│          → Odoo XML-RPC (account.analytic.line)         │
│          → Upsert 7,236+ records into timesheets table  │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                   USER OPENS DASHBOARD                  │
│                                                         │
│  Vercel (site/index.html loads in browser)              │
│      → GET get-staff-config  (page load)                │
│      → GET get-aggregates?period=ALL  (page load)       │
│          → Supabase PostgreSQL query                    │
│          → Returns KPIs + employees + projects + tasks  │
│      → Renders charts, tables, KPI cards                │
│                                                         │
│  User clicks Apply filter:                              │
│      → GET get-aggregates?period=3M&employee=Jyoti...   │
│      → Re-renders everything                            │
│                                                         │
│  User clicks employee row:                              │
│      → GET get-employee?name=Jyoti+Batra                │
│      → Opens drill-down panel with pie chart            │
│                                                         │
│  User clicks project row:                               │
│      → GET get-project?name=Website+Redesign            │
│      → Opens drill-down panel with bar chart            │
└─────────────────────────────────────────────────────────┘
```

---

## 10. Scheduled Sync Setup

The sync runs automatically every 30 minutes using Supabase's `pg_cron` extension, which triggers an HTTP POST to the `sync-odoo` edge function via `pg_net`.

**To manually trigger a sync at any time:**

```powershell
# PowerShell
Invoke-WebRequest -Method POST -Uri "https://deppuufhjctbusypehvy.supabase.co/functions/v1/sync-odoo" -UseBasicParsing
```

```bash
# Mac/Linux
curl -X POST https://deppuufhjctbusypehvy.supabase.co/functions/v1/sync-odoo
```

**To check sync schedule in Supabase SQL Editor:**
```sql
SELECT * FROM cron.job;
```

**To view sync history:**
```sql
SELECT * FROM cron.job_run_details ORDER BY start_time DESC LIMIT 20;
```

---

## 11. Vercel Deployment

**Live site:** Hosted on Vercel from the `site/` folder.

**Deployment config:**
- **Root Directory:** `site`
- **Framework Preset:** Other
- **Build Command:** (empty)
- **Output Directory:** (empty)

**Auto-deploy:** Every push to the `main` branch of `SauravBhandari93/pv-timesheet-dashboard` triggers an automatic Vercel redeploy.

**What gets deployed:** Only the `site/` folder contents:
```
site/
├── index.html     ← full dashboard (HTML + CSS + JS, ~87KB)
└── PV_Logo.png    ← company logo (~10KB)
```

---

## 12. How to Maintain Going Forward

### Update staff config (new hire, resignation, billability keywords)

1. Go to Supabase dashboard → SQL Editor
2. Run:
```sql
UPDATE staff_config SET config = '{
  "new_employees": ["New Person Name"],
  "resigned_employees": ["Old Person Name"],
  "non_billable_tasks": ["Leave", "Fun Friday", "Holiday", "Public Holiday", "Internal Meeting"],
  "leave_tasks": ["Leave", "Holiday", "Public Holiday"]
}', updated_at = NOW()
WHERE id = 1;
```
3. Changes take effect immediately — no redeploy needed

### Force a fresh sync from Odoo

```powershell
Invoke-WebRequest -Method POST -Uri "https://deppuufhjctbusypehvy.supabase.co/functions/v1/sync-odoo" -UseBasicParsing
```

### Deploy updated edge function code

After changing any file in `supabase/functions/`:

```bash
# Redeploy specific function
supabase functions deploy sync-odoo --no-verify-jwt

# Or redeploy all
supabase functions deploy sync-odoo        --no-verify-jwt
supabase functions deploy get-aggregates   --no-verify-jwt
supabase functions deploy get-employee     --no-verify-jwt
supabase functions deploy get-project      --no-verify-jwt
supabase functions deploy get-staff-config --no-verify-jwt
```

### Update the frontend dashboard

1. Edit `site/index.html`
2. Push to GitHub → Vercel auto-redeploys

If you edit `templates/dashboard.html` (the original), remember to also copy changes to `site/index.html`.

### Check Supabase function logs

Supabase dashboard → Edge Functions → click function name → **Logs** tab.

Useful for debugging sync issues or seeing error messages.

### Check data in database

Supabase dashboard → Table Editor → `timesheets`

Or via SQL:
```sql
-- Total records
SELECT COUNT(*) FROM timesheets;

-- Most recent sync
SELECT MAX(synced_at) FROM timesheets;

-- Records per employee
SELECT employee, COUNT(*), SUM(hours) FROM timesheets GROUP BY employee ORDER BY SUM(hours) DESC;

-- Records for a specific month
SELECT * FROM timesheets WHERE date >= '2026-04-01' AND date < '2026-05-01';
```

---

## 13. Troubleshooting

### Dashboard shows no data

1. Check the browser console (F12) for errors
2. Test the edge function directly:
   ```
   https://deppuufhjctbusypehvy.supabase.co/functions/v1/get-aggregates?period=ALL
   ```
3. If that returns `{"employees":[],...}`, the `timesheets` table may be empty — trigger a manual sync

### Sync returns 0 records

1. Check Odoo credentials are set correctly:
   ```bash
   supabase secrets list
   ```
2. Check Supabase function logs for the error message
3. Verify the Odoo URL is reachable and the API key is valid

### Employee names showing as numbers (e.g. "5", "8")

This was a bug in the original XML parser — fixed in the current `_shared/odoo.ts`. If it reappears:
1. Redeploy `sync-odoo`: `supabase functions deploy sync-odoo --no-verify-jwt`
2. Trigger a manual sync
3. Check that `employee` column has real names: `SELECT DISTINCT employee FROM timesheets LIMIT 20;`

### VS Code shows red errors in edge function files

These are false positives — VS Code is using the Node.js TypeScript checker on Deno files. Fix:
1. Install the **Deno** extension by denoland (`denoland.vscode-deno`)
2. Reload VS Code

The code deploys and runs correctly regardless of these editor errors.

### Vercel shows wrong content / old data

Vercel serves `site/index.html` as a static file. The data comes from Supabase at runtime (in the browser). If data is stale:
- Trigger a manual sync (see above)
- The Vercel deployment itself doesn't affect data — it only serves the HTML file

### CORS errors in browser console

If you see `Access-Control-Allow-Origin` errors, the edge functions include CORS headers for all origins (`*`). This should not happen. If it does:
1. Verify the function was deployed with `--no-verify-jwt`
2. Check that the `OPTIONS` preflight handler is present in the function code

---

## Quick Reference

| Task | Command / URL |
|---|---|
| Manual sync | `POST https://deppuufhjctbusypehvy.supabase.co/functions/v1/sync-odoo` |
| Test aggregates | `GET https://deppuufhjctbusypehvy.supabase.co/functions/v1/get-aggregates?period=ALL` |
| Run frontend locally | `cd site && python -m http.server 3000` |
| Deploy edge function | `supabase functions deploy <name> --no-verify-jwt` |
| Supabase dashboard | https://supabase.com/dashboard/project/deppuufhjctbusypehvy |
| GitHub repo | https://github.com/SauravBhandari93/pv-timesheet-dashboard |

---

*Last updated: April 2026*
