# PV Timesheet Dashboard — Complete Project Documentation

> Everything you need to understand, set up, and run the project from scratch.

---

## Table of Contents

1. [What Is This Project?](#1-what-is-this-project)
2. [Technology Stack](#2-technology-stack)
3. [Project Structure](#3-project-structure)
4. [Prerequisites](#4-prerequisites)
5. [Step-by-Step Setup (Local Dev)](#5-step-by-step-setup-local-dev)
6. [Environment Variables](#6-environment-variables)
7. [Running the App](#7-running-the-app)
8. [API Reference](#8-api-reference)
9. [Odoo Integration — What We Call & Why](#9-odoo-integration--what-we-call--why)
10. [Data Processing Logic](#10-data-processing-logic)
11. [Staff Configuration](#11-staff-configuration)
12. [Frontend Dashboard](#12-frontend-dashboard)
13. [Deployment (Render / Heroku)](#13-deployment-render--heroku)
14. [Common Tasks & Commands](#14-common-tasks--commands)
15. [Known Limitations](#15-known-limitations)

---

## 1. What Is This Project?

**PV Timesheet Dashboard** is an internal web dashboard that pulls timesheet data from an **Odoo ERP** instance and visualizes it as charts, tables, and KPIs — giving the team a clear picture of:

- How many hours each employee logged
- Which hours were billable vs. leave/non-billable
- Which projects consumed the most time
- Individual employee and project drill-downs

**Who is it for?** Team leads and managers at PV who want a quick visual summary of what the team has been working on, without having to navigate Odoo's clunky reporting UI.

**How does it work (one-liner)?**
> A Python/Flask backend authenticates with Odoo via XML-RPC, fetches all timesheet records, aggregates them, and serves them to a single-page HTML dashboard.

---

## 2. Technology Stack

| Layer | Technology | Why |
|---|---|---|
| Backend | Python 3.11 + Flask | Lightweight, easy to deploy |
| Odoo Integration | XML-RPC (`xmlrpc.client`) | Odoo's standard external API |
| Caching | In-memory dict (Python) | Simple, no Redis needed |
| WSGI Server | Gunicorn | Production-grade, Render/Heroku compatible |
| Frontend | Vanilla HTML/CSS/JS (no build step) | No Node.js, no bundler, just open the browser |
| Charts | Chart.js 4 (CDN) | Easy integration, good-looking charts |
| Icons | Lucide (CDN) | Clean icon set |
| Env vars | python-dotenv | Load `.env` file locally |

**No Node.js. No npm. No webpack.** This is a pure Python + plain-HTML project. The only package manager you need is `pip`.

---

## 3. Project Structure

```
pv-timesheet-dashboard/
│
├── app.py                  ← Flask app (backend, API, data processing)
├── requirements.txt        ← Python dependencies
├── runtime.txt             ← Python version for Render/Heroku
├── Procfile                ← Gunicorn startup command for deployment
│
├── .env                    ← Your local secrets (git-ignored, you create this)
├── .env.template           ← Template showing required env vars
├── .gitignore              ← Ignores .env, __pycache__, venv/
│
├── staff_config.json       ← Team configuration (new hires, resigned, billability rules)
│
├── templates/
│   └── dashboard.html      ← The entire frontend: HTML + CSS + JS in one file
│
├── static/
│   ├── style.css           ← Tiny CSS reset (4 lines)
│   └── script.js           ← Legacy table loader (mostly replaced by dashboard.html)
│
├── public/
│   └── PV_Logo.png         ← Company logo
│
├── CLAUDE.md               ← Notes for AI assistant (Claude Code)
├── README.md               ← Short project overview
└── setup.md                ← This file
```

**Key insight:** The entire frontend lives in `templates/dashboard.html` (~2300 lines). There is no React, no Vue, no build step. Just open it in a browser.

---

## 4. Prerequisites

Before you start, make sure you have:

### 4.1 Python 3.11+

Check if you have it:
```bash
python --version
# or
python3 --version
```

If not, download from https://python.org/downloads/ — install Python 3.11 or higher.

### 4.2 pip (Python package manager)

pip comes with Python. Verify:
```bash
pip --version
```

### 4.3 Odoo credentials

You need four pieces of information from your Odoo instance (ask your Odoo admin):
- **Odoo URL** — e.g. `https://yourcompany.odoo.com`
- **Database name** — e.g. `yourcompany`
- **Your Odoo email/username** — e.g. `you@yourcompany.com`
- **API Key** — Generate in Odoo: `Settings → My Profile → Account Security → API Keys → New`

### 4.4 Git (optional but recommended)

```bash
git --version
```

---

## 5. Step-by-Step Setup (Local Dev)

Follow every step in order.

### Step 1 — Clone the repository

```bash
git clone https://github.com/your-org/pv-timesheet-dashboard.git
cd pv-timesheet-dashboard
```

Or if you already have the folder:
```bash
cd pv-timesheet-dashboard
```

### Step 2 — Create a virtual environment

A virtual environment keeps project dependencies isolated from your system Python.

```bash
# Create the virtual environment (creates a folder named 'venv')
python -m venv venv
```

### Step 3 — Activate the virtual environment

**Windows (Command Prompt):**
```cmd
venv\Scripts\activate
```

**Windows (PowerShell):**
```powershell
venv\Scripts\Activate.ps1
```

**Mac/Linux:**
```bash
source venv/bin/activate
```

After activation, your terminal prompt will show `(venv)` at the beginning. You must activate it every time you open a new terminal.

### Step 4 — Install Python dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `flask` — web framework that serves the dashboard
- `gunicorn` — production WSGI server (not needed for local dev, but included)
- `python-dotenv` — reads `.env` file automatically

`xmlrpc.client` is built into Python standard library — no install needed.

Verify installation:
```bash
pip list
```

You should see `Flask`, `gunicorn`, and `python-dotenv` in the list.

### Step 5 — Create your `.env` file

Copy the template:

**Windows:**
```cmd
copy .env.template .env
```

**Mac/Linux:**
```bash
cp .env.template .env
```

Now open `.env` in any text editor and fill in your values:

```env
ODOO_URL=https://yourcompany.odoo.com
ODOO_DB=yourcompany
ODOO_USERNAME=you@yourcompany.com
ODOO_API_KEY=your_api_key_here
CACHE_MINUTES=5
```

**Important:** `.env` is git-ignored — it will never be committed. Your credentials stay local.

### Step 6 — (Optional) Update staff_config.json

Open `staff_config.json` and update it for your team:

```json
{
  "new_employees": ["Name of new hire"],
  "resigned_employees": ["Name of ex-employee"],
  "non_billable_tasks": ["Leave", "Fun Friday", "Holiday", "Public Holiday", "Internal Meeting"],
  "leave_tasks": ["Leave", "Holiday", "Public Holiday"]
}
```

This file controls which task names count as "leave" or "non-billable" — see [Section 11](#11-staff-configuration) for full details.

### Step 7 — Run the app

```bash
python app.py
```

You should see:
```
 * Running on http://127.0.0.1:5000
 * Debug mode: on
```

Open your browser and go to: **http://localhost:5000**

The dashboard will load. On first visit it fetches data from Odoo (may take 3-10 seconds depending on your Odoo's speed), then caches it for 5 minutes.

---

## 6. Environment Variables

All configuration goes in `.env` (local dev) or as environment variables on the hosting platform (production).

| Variable | Required | Default | Description |
|---|---|---|---|
| `ODOO_URL` | Yes | — | Your Odoo instance URL. Must include `https://` or `http://`. Example: `https://acme.odoo.com` |
| `ODOO_DB` | Yes | — | Odoo database name. Usually matches your subdomain. Example: `acme` |
| `ODOO_USERNAME` | Yes | — | Email address you use to log into Odoo |
| `ODOO_API_KEY` | Yes | — | API key from Odoo (Settings → My Profile → API Keys) |
| `CACHE_MINUTES` | No | `5` | How long (in minutes) to cache Odoo data in memory. Increase for slower Odoo instances. |

**How to find your Odoo DB name:**
Log into Odoo → click the grid icon (top-left) → the URL in your browser shows `https://yourdb.odoo.com` — `yourdb` is the DB name.

**How to generate an API key in Odoo:**
Settings → My Profile → Account Security → API Keys → New → give it a name → copy the key immediately (it's shown only once).

---

## 7. Running the App

### Development mode (recommended for local use)

```bash
python app.py
```

- Runs Flask's built-in dev server
- Auto-reloads on code changes
- Shows detailed error pages
- NOT suitable for production (single-threaded, no security hardening)
- Available at: http://localhost:5000

### Production mode (Gunicorn)

```bash
gunicorn app:app --workers=2 --threads=2 --timeout=120
```

- `workers=2` — 2 parallel worker processes (each has its own cache)
- `threads=2` — 2 threads per worker (handles concurrent requests)
- `timeout=120` — kills a request if it takes longer than 120s (Odoo can be slow)
- Available at: http://localhost:8000

### Clear the data cache (without restarting)

```bash
# In another terminal while the app is running:
curl http://localhost:5000/api/cache/clear
```

Or just open that URL in your browser. Useful when you want fresh Odoo data immediately, without waiting for the 5-minute TTL.

---

## 8. API Reference

All endpoints are served by Flask (`app.py`). The frontend (`dashboard.html`) calls these endpoints via `fetch()`.

### `GET /`

**What it does:** Serves the main dashboard HTML page.

**Response:** HTML (`templates/dashboard.html` rendered by Jinja2)

---

### `GET /api/aggregates`

**What it does:** The main data endpoint. Fetches timesheets from cache (or Odoo if cache is cold), filters them by the given params, aggregates into KPIs + employee stats + project stats + task list, and returns JSON.

**Query parameters:**

| Param | Type | Default | Values |
|---|---|---|---|
| `period` | string | `ALL` | `ALL`, `3M`, `6M`, `MONTH` |
| `month` | string | `null` | `YYYY-MM` format (only used when `period=MONTH`) |
| `employee` | string | `ALL` | Employee full name, or `ALL` |
| `project` | string | `ALL` | Project full name, or `ALL` |
| `billable` | string | `null` | `true` to show only billable, `false` for non-billable, omit for all |

**Example request:**
```
GET /api/aggregates?period=3M&employee=John+Smith&billable=true
```

**Response shape:**
```json
{
  "kpi": {
    "total_hours": 537.7,
    "employees_count": 9,
    "tasks_count": 104,
    "projects_count": 25,
    "leave_hours": 143.0
  },
  "employees": [
    {
      "no": 1,
      "name": "John Smith",
      "short": "J. Smith",
      "total": 65.0,
      "bill": 25.0,
      "leave": 8.0,
      "billPct": 0.3846,
      "projects": 3,
      "tasks": 14,
      "teamPct": 0.1209
    }
  ],
  "projects": [
    {
      "no": 1,
      "name": "Website Redesign",
      "hrs": 75.2,
      "tasks": 21,
      "pct": 0.13976,
      "emps": 5,
      "avgHrs": 3.58,
      "bill": 60.5,
      "billPct": 0.8041
    }
  ],
  "tasks": [
    {
      "proj": "Website Redesign",
      "task": "Homepage wireframe review",
      "desc": "Homepage wireframe review",
      "hrs": 2.0,
      "employee": "John Smith",
      "date": "2025-03-10",
      "billable": true
    }
  ],
  "_filters": {
    "period": "3M",
    "month": null,
    "employee": "John Smith",
    "project": "ALL",
    "billable": "true"
  }
}
```

**Why the frontend calls this:** Every time the user clicks "Apply" on the filter bar, the dashboard calls `/api/aggregates` with the current filter state and re-renders all charts and tables.

---

### `GET /api/employee?name=<name>`

**What it does:** Returns a detailed breakdown for a single employee — their total/billable hours, every task they logged, and a per-project summary.

**Query parameters:**

| Param | Required | Description |
|---|---|---|
| `name` | Yes | Exact employee name (case-sensitive) |

**Example request:**
```
GET /api/employee?name=John+Smith
```

**Response shape:**
```json
{
  "name": "John Smith",
  "total": 65.0,
  "bill": 25.0,
  "tasks": [
    {
      "proj": "Website Redesign",
      "task": "Homepage wireframe",
      "desc": "Homepage wireframe",
      "hrs": 2.0,
      "employee": "John Smith",
      "date": "2025-03-10",
      "billable": true
    }
  ],
  "projects": [
    {
      "name": "Website Redesign",
      "hrs": 20.0,
      "tasks": 5
    }
  ]
}
```

**Why the frontend calls this:** When a user clicks on a row in the Employees table, the dashboard opens a side panel and calls `/api/employee` to show that person's detailed breakdown and a pie chart of their time by project.

---

### `GET /api/project?name=<name>`

**What it does:** Returns a detailed breakdown for a single project — total hours, every task logged against it, and a per-employee summary.

**Query parameters:**

| Param | Required | Description |
|---|---|---|
| `name` | Yes | Exact project name (case-sensitive) |

**Example request:**
```
GET /api/project?name=Website+Redesign
```

**Response shape:**
```json
{
  "name": "Website Redesign",
  "total": 75.2,
  "tasks": [
    {
      "proj": "Website Redesign",
      "task": "Homepage wireframe",
      "desc": "Homepage wireframe",
      "hrs": 2.0,
      "employee": "John Smith",
      "date": "2025-03-10",
      "billable": true
    }
  ],
  "employees": [
    {
      "employee": "John Smith",
      "hrs": 20.0
    }
  ]
}
```

**Why the frontend calls this:** When a user clicks on a row in the Projects table, the dashboard opens a side panel and calls `/api/project` to show that project's detailed breakdown and a bar chart of hours by employee.

---

### `GET /api/staff-config`

**What it does:** Returns the contents of `staff_config.json` — the list of new employees, resigned employees, non-billable task keywords, and leave task keywords.

**Response shape:**
```json
{
  "new_employees": ["Sahil Rana"],
  "resigned_employees": ["Anant Jain"],
  "non_billable_tasks": ["Leave", "Fun Friday", "Holiday"],
  "leave_tasks": ["Leave", "Holiday", "Public Holiday"]
}
```

**Why the frontend calls this:** On page load, the dashboard fetches staff config to know which employees to badge as "NEW" or "RESIGNED" and which keywords to use client-side for any billability display logic.

---

### `GET /api/timesheets`

**What it does:** Returns the raw, unprocessed list of Odoo timesheet records from the cache. This is the legacy endpoint — it was the original API before the more sophisticated `/api/aggregates` was built.

**Response:** Array of raw Odoo records.

**Note:** The main dashboard (`dashboard.html`) does NOT use this endpoint anymore. It's kept for backwards compatibility and debugging.

---

### `GET /api/cache/clear`

**What it does:** Immediately invalidates the in-memory cache, forcing the next API call to re-fetch fresh data from Odoo.

**Response:**
```json
{"status": "cache cleared"}
```

**When to use this:**
- You just logged new timesheets in Odoo and don't want to wait 5 minutes
- Data looks stale or wrong and you want to force a refresh
- During development/debugging

**Caveat:** If running with multiple Gunicorn workers (production), this only clears the cache on the worker that handled the request — other workers still have their own cached data.

---

### `GET /public/<filename>`

**What it does:** Serves static files from the `public/` directory.

**Example:** `GET /public/PV_Logo.png` → returns the PV company logo

**Used by:** `dashboard.html` to display the logo in the header.

---

## 9. Odoo Integration — What We Call & Why

The backend connects to Odoo using **XML-RPC**, which is Odoo's official external API protocol. It requires no Odoo add-ons — it's available in every Odoo instance by default.

### 9.1 Why XML-RPC?

Odoo provides two external APIs:
- **XML-RPC** — older, universal, available in all Odoo versions (8, 12, 16, 17…)
- **JSON-RPC** — newer, available in Odoo 14+

We use XML-RPC because it's supported everywhere and requires no additional setup. Python's standard library includes `xmlrpc.client` — zero extra dependencies.

### 9.2 Authentication Flow

Every time the cache needs a refresh, `app.py` does this:

```
Step 1: Call /xmlrpc/2/common → authenticate()
        Sends: DB name, username, API key
        Receives: uid (user ID integer, e.g. 7)

Step 2: Call /xmlrpc/2/object → execute_kw()
        Sends: DB name, uid, API key, model name, method, args
        Receives: list of records
```

**Why two steps?** Odoo separates authentication (step 1) from data access (step 2). The `uid` from step 1 proves who you are for every step 2 call.

### 9.3 What Odoo Model We Query

**Model:** `account.analytic.line`

This is Odoo's internal timesheet model. Every time an employee logs hours in Odoo Timesheets, a record is created in this model. Think of it as a database table where each row = one timesheet entry.

### 9.4 What Fields We Request

```python
fields = ["employee_id", "unit_amount", "name", "date", "project_id", "task_id"]
```

| Field | Odoo Type | What It Contains |
|---|---|---|
| `employee_id` | Many2one | `[123, "John Smith"]` — ID and display name of the employee |
| `unit_amount` | Float | Hours logged for this entry (e.g. `2.5`) |
| `name` | Char | Description the employee typed (e.g. "Fixed login bug") |
| `date` | Date | Date the work was done (e.g. `"2025-03-15"`) |
| `project_id` | Many2one | `[456, "Website Redesign"]` — ID and name of the project |
| `task_id` | Many2one | `[789, "Bug Fixes"]` — ID and name of the Odoo task |

**Why these specific fields?**
- `employee_id` → who did the work
- `unit_amount` → how many hours
- `name` → what they described doing
- `date` → when they did it
- `project_id` → which project (for grouping and filtering)
- `task_id` → which task (used for billability keyword matching)

**We fetch ALL records** (no domain filter / date range filter at the Odoo API level) and do all filtering in Python. This means:
- One Odoo call per cache period, regardless of filters
- Filters applied server-side in `filter_records()`
- Cache stores the full unfiltered dataset

### 9.5 Full Odoo API Call

```python
import xmlrpc.client

common = xmlrpc.client.ServerProxy("https://yourcompany.odoo.com/xmlrpc/2/common")
uid = common.authenticate("yourdb", "you@email.com", "api_key", {})

models = xmlrpc.client.ServerProxy("https://yourcompany.odoo.com/xmlrpc/2/object")
records = models.execute_kw(
    "yourdb",                    # DB name
    uid,                         # User ID from authentication
    "api_key",                   # API key (used as password)
    "account.analytic.line",     # Model (timesheet entries)
    "search_read",               # Method: search + read in one call
    [[]],                        # Domain: [] means no filter (fetch all)
    {
        "fields": [              # Only fetch these fields (reduces payload)
            "employee_id",
            "unit_amount",
            "name",
            "date",
            "project_id",
            "task_id"
        ]
    }
)
```

---

## 10. Data Processing Logic

All data processing happens in `app.py`. Here is what each key function does:

### `fetch_timesheets()` (line ~69)

- Reads env vars (`ODOO_URL`, `ODOO_DB`, `ODOO_USERNAME`, `ODOO_API_KEY`)
- Validates that ODOO_URL starts with `http://` or `https://`
- Authenticates with Odoo XML-RPC → gets `uid`
- Calls `search_read` on `account.analytic.line` → gets all timesheet records
- Returns raw list of dicts

### `get_cached_data()` (line ~105)

- Checks if `CACHE["data"]` exists and is younger than `CACHE_MINUTES`
- If yes → returns cached data immediately (fast)
- If no → calls `fetch_timesheets()`, stores result in `CACHE`, returns it

### `is_billable(record, non_billable_keywords)` (line ~50)

The billability engine. How it works:

1. Concatenates `task_id` display name + `name` field + `project_id` display name → one lowercase string
2. Checks if ANY keyword from `non_billable_tasks` (in staff_config.json) is a substring of that string
3. If a keyword matches → `return False` (non-billable)
4. If no keyword matches → `return True` (billable by default)

**Example:** If `non_billable_tasks = ["Leave", "Fun Friday"]` and a record's task is `"Annual Leave"`, the check finds "leave" (lowercase) inside "annual leave" → marks it non-billable.

**Why keyword-based instead of Odoo's native billability field?**
Odoo has fields like `is_billable`, `to_invoice`, and `invoice_status` — but these vary by Odoo version, module setup, and configuration. Many Odoo instances don't have them set correctly. Keyword matching on task names is reliable because your team controls what task names they use.

### `is_leave(record, leave_keywords)` (line ~62)

Same logic as `is_billable`, but checks against `leave_tasks` keywords. Returns `True` if it's a leave/holiday entry. Used to count leave hours separately in KPIs.

### `filter_records(records, period, month, employee, project, billable, non_billable_keywords)` (line ~236)

Applies filters to the full record list:

1. **Date filter:**
   - `ALL` → no filter
   - `3M` → last 90 days from today
   - `6M` → last 180 days from today
   - `MONTH` → specific calendar month (e.g., `2025-03`)

2. **Employee filter:** `r["employee_id"][1] == employee` (exact name match)

3. **Project filter:** `r["project_id"][1] == project` (exact name match)

4. **Billable filter:** calls `is_billable()` and keeps/discards based on `billable` param

### `process_timesheets(records, staff_config)` (line ~116)

Takes filtered records and builds the response. Produces:

**KPIs:**
- `total_hours` = sum of all `unit_amount`
- `employees_count` = unique employees who logged time (excluding resigned)
- `tasks_count` = total number of timesheet entries
- `projects_count` = number of unique projects
- `leave_hours` = sum of hours where `is_leave()` is True

**Per-employee stats** (sorted by total hours, descending):
- `total`, `bill`, `leave`, `billPct`, `projects` (count), `tasks` (count), `teamPct`

**Per-project stats** (sorted by hours, descending):
- `hrs`, `tasks`, `emps` (count), `bill`, `billPct`, `avgHrs`

**Task list:** All individual records (flat array) with billable flag added.

---

## 11. Staff Configuration

`staff_config.json` is the main configuration file for the team. You can edit it without restarting the server.

```json
{
  "new_employees": ["Sahil Rana"],
  "resigned_employees": ["Anant Jain", "Umesh Chandra Dani"],
  "non_billable_tasks": [
    "Leave",
    "Fun Friday",
    "Holiday",
    "Public Holiday",
    "Internal Meeting"
  ],
  "leave_tasks": [
    "Leave",
    "Holiday",
    "Public Holiday"
  ]
}
```

### What each field does

| Field | Effect |
|---|---|
| `new_employees` | Dashboard shows a green "NEW" badge next to their name in the employees table |
| `resigned_employees` | Dashboard shows a red "RESIGNED" badge, their row is dimmed, and they're excluded from the active employee count in KPIs |
| `non_billable_tasks` | Keywords: any timesheet entry whose task name, description, or project name contains one of these strings (case-insensitive) is marked as non-billable |
| `leave_tasks` | Subset of the above: entries matching these are counted as "Leave + Holiday" hours in the KPI card |

### How to update

1. Open `staff_config.json` in any text editor
2. Add/remove names or keywords
3. Save the file
4. The next API call will use the updated config — no restart needed

### Important: keyword matching is substring-based

If `non_billable_tasks` contains `"Leave"`, then ANY entry where the task name, description, or project name contains "leave" (case-insensitive) is marked non-billable. This means:
- "Annual Leave" → non-billable ✓
- "Leave Application" → non-billable ✓
- "Interleave Algorithm" → also non-billable (false positive — add more specific keywords if this happens)

---

## 12. Frontend Dashboard

The entire UI lives in `templates/dashboard.html`. It is a ~2300-line single-page app with all CSS and JavaScript inline. There is no build step, no framework, no npm.

### 12.1 Navigation Tabs

| Tab | What it shows |
|---|---|
| Overview | KPI cards + 7 charts (project distribution, employee hours, billability breakdown) |
| Projects | Sortable projects table with drill-down side panel |
| Employees | Sortable employees table with drill-down side panel |
| Tasks | Flat task list with search, project filter, employee filter |

### 12.2 Filter Bar

Located below the header, always visible:

- **Period:** All time / Last 3 months / Last 6 months / Specific month
- **Month picker:** Only visible when "Specific month" is selected
- **Employee dropdown:** All employees in the dataset
- **Project dropdown:** All projects in the dataset
- **Billable only:** Checkbox to show only billable entries
- **Apply:** Sends the filter to `/api/aggregates` and re-renders everything
- **Reset:** Clears all filters back to defaults

### 12.3 Charts (powered by Chart.js 4 from CDN)

| Chart ID | Type | What it shows | Tab |
|---|---|---|---|
| `ov-pb` | Bar | Top 8 projects by billable hours | Overview |
| `ov-pd` | Doughnut | Project distribution (top 6 share of total hours) | Overview |
| `ov-eg` | Stacked bar | Each employee's total hours split into billable vs. other | Overview |
| `ov-bl` | Bar | Each employee's billability rate (green ≥80%, yellow 50-80%, red <50%) | Overview |
| `ov-sd` | Doughnut | Team split: Billable hours / Leave hours / Other | Overview |
| `ov-er` | Horizontal bar | Top 8 employees by total hours (ranking) | Overview |
| `ov-te` | Bar | Top 8 employees by task count | Overview |
| `ddp-ec` | Bar | Hours per employee for the selected project (drill-down panel) | Projects |
| `dde-pie` | Pie | Time allocation by project for the selected employee (drill-down panel) | Employees |

### 12.4 Data Loading Flow

This is the exact sequence of events when the page loads or filters are applied:

```
1. Page loads
   │
   ├── loadStaffConfig()
   │   └── GET /api/staff-config
   │       └── Stores new/resigned employee lists
   │
   └── applyGlobalFilters()
       └── GET /api/aggregates?period=ALL&...
           │
           ├── stores: employees[], projects[], taskData[], lastAggregates{}
           │
           ├── initOv()           → Update KPI card numbers and period banner
           ├── rpt()              → Render projects table rows
           ├── ret()              → Render employees table rows (with NEW/RESIGNED badges)
           ├── itf()              → Destroy old charts → draw all 7 charts
           ├── ft()               → Render tasks table + populate filter dropdowns
           └── attachDrillHandlers() → Add click listeners to table rows
```

### 12.5 Drill-down Panels

**Click a project row:**
1. `showProject(name)` is called
2. `GET /api/project?name=<name>` is fetched
3. Side panel slides open showing:
   - Project name, total hours, task count, billability %, employee count, avg hrs/task
   - Table of all tasks (sorted by hours)
   - Bar chart of hours per employee

**Click an employee row:**
1. `showEmployee(name)` is called
2. `GET /api/employee?name=<name>` is fetched
3. Side panel slides open showing:
   - Employee name, total hours, billable hours, billability %, projects count, tasks count, leave hours
   - Table of tasks by project
   - Pie chart of time allocation by project

### 12.6 Theme (Light / Dark)

- **Toggle:** Sun/moon icon button in the top-right header
- **Persistence:** Saved to `localStorage` with key `pv-theme`
- **Default:** Follows system preference (`prefers-color-scheme`)
- **Implementation:** Sets `data-theme` attribute on `<html>` tag; all colors use CSS variables

### 12.7 KPI Cards

| Card | Color | Value Source | Subtitle |
|---|---|---|---|
| Total Team Hours | Teal | `kpi.total_hours` | Number of active employees |
| Billable Hours | Indigo | Calculated from employees data | Team billability % |
| Leave + Holiday | Pink | `kpi.leave_hours` | "hrs non-billable absence" |
| Projects Active | Orange | `kpi.projects_count` | Average hours per project |

---

## 13. Deployment (Render / Heroku)

### 13.1 Procfile

The `Procfile` tells Render/Heroku how to start the app:

```
web: gunicorn app:app --workers=2 --threads=2 --timeout=120
```

### 13.2 Deploy to Render

1. Push your code to GitHub (do NOT commit `.env` — it's git-ignored)
2. Go to https://render.com → New Web Service → connect your repo
3. Set environment variables in Render dashboard (same as your `.env` file):
   - `ODOO_URL`
   - `ODOO_DB`
   - `ODOO_USERNAME`
   - `ODOO_API_KEY`
   - `CACHE_MINUTES` (optional, default 5)
4. Build command: `pip install -r requirements.txt`
5. Start command: _(auto-detected from Procfile)_
6. Deploy

### 13.3 Python Version

`runtime.txt` pins the Python version:
```
python-3.11.9
```

Render and Heroku both read this file to select the correct Python runtime.

### 13.4 Cache in Production

With `--workers=2`, Gunicorn runs 2 separate Python processes. **Each worker has its own independent cache.** This means:
- Requests routed to worker 1 use worker 1's cache
- Requests routed to worker 2 use worker 2's cache
- `/api/cache/clear` only clears the cache of the worker that received the request

For a team of ~15 people this is fine — data is at most 5 minutes stale per worker. If you need stricter cache coherence, reduce to `--workers=1` or add Redis caching.

---

## 14. Common Tasks & Commands

```bash
# First-time setup
python -m venv venv
source venv/bin/activate     # Mac/Linux
venv\Scripts\activate        # Windows
pip install -r requirements.txt
cp .env.template .env        # Then edit .env with your credentials

# Run in development
python app.py

# Run in production mode
gunicorn app:app --workers=2 --threads=2 --timeout=120

# Force fresh data from Odoo
curl http://localhost:5000/api/cache/clear

# Test the main API
curl "http://localhost:5000/api/aggregates?period=3M" | python -m json.tool

# Test employee drill-down
curl "http://localhost:5000/api/employee?name=John+Smith" | python -m json.tool

# Test project drill-down
curl "http://localhost:5000/api/project?name=Website+Redesign" | python -m json.tool

# Check what staff config is loaded
curl http://localhost:5000/api/staff-config | python -m json.tool

# Deactivate the virtual environment when done
deactivate
```

---

## 15. Known Limitations

| Limitation | Details |
|---|---|
| **No authentication** | The dashboard has no login page. Anyone on the network can access it. Suitable for internal/intranet use only. |
| **Per-worker cache** | Multi-worker Gunicorn deployments have independent caches. See [Section 13.4](#134-cache-in-production). |
| **No real-time updates** | Data refreshes only when the user clicks Apply or the cache expires. No WebSocket / push updates. |
| **No export** | No CSV or Excel export. The dashboard is read-only visualization. |
| **Keyword billability** | Billability is determined by keyword matching on task names, not Odoo's native fields. A task named "Interleaved Processing" would be marked non-billable if "leave" is a keyword. |
| **Full-fetch from Odoo** | All timesheet records are fetched every cache period with no date filter. For very large Odoo instances (100k+ records), this may be slow on first load. |
| **No rate limiting** | The API has no rate limiting. Not suitable for public internet exposure. |
| **No audit trail** | No logging of who viewed what. |

---

*Last updated: April 2026*
