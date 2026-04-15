from flask import Flask, render_template, jsonify
import xmlrpc.client
import os
from datetime import datetime, timedelta

app = Flask(__name__)

ODOO_URL = os.getenv("ODOO_URL")
ODOO_DB = os.getenv("ODOO_DB")
ODOO_USERNAME = os.getenv("ODOO_USERNAME")
ODOO_API_KEY = os.getenv("ODOO_API_KEY")

CACHE = {"data": None, "timestamp": None}
CACHE_MINUTES = int(os.getenv("CACHE_MINUTES", 5))

def fetch_timesheets():
    common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
    uid = common.authenticate(ODOO_DB, ODOO_USERNAME, ODOO_API_KEY, {})

    models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")

    records = models.execute_kw(
        ODOO_DB,
        uid,
        ODOO_API_KEY,
        "account.analytic.line",
        "search_read",
        [[]],
        {"fields": ["employee_id", "unit_amount", "name", "date"]}
    )

    return records

def get_cached_data():
    if CACHE["data"] and CACHE["timestamp"]:
        if datetime.now() - CACHE["timestamp"] < timedelta(minutes=CACHE_MINUTES):
            return CACHE["data"]

    data = fetch_timesheets()
    CACHE["data"] = data
    CACHE["timestamp"] = datetime.now()
    return data

@app.route("/")
def index():
    return render_template("dashboard.html")

@app.route("/api/timesheets")
def timesheets():
    data = get_cached_data()
    return jsonify(data)

@app.route("/api/cache/clear")
def clear_cache():
    CACHE["data"] = None
    return {"status": "cache cleared"}

if __name__ == "__main__":
    app.run(debug=True)