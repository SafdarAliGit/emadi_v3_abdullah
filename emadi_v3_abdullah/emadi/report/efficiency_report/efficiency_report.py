import frappe
import re


def execute(filters=None):
    if not filters:
        filters = {}

    date = filters.get("date")

    if not date:
        frappe.throw("Please select a Date")

    data = get_merged_looms_data(date)
    columns = get_columns()

    return columns, data


def get_columns():
    return [
        {"label": "Loom",           "fieldname": "a_loom",               "fieldtype": "Data",     "width": 120},
        {"label": "Quality Name",   "fieldname": "a_sizing_name",        "fieldtype": "Data",     "width": 140},
        {"label": "RPM",            "fieldname": "a_rpm",                "fieldtype": "Data",     "width": 80},
        {"label": "100% UNIT",      "fieldname": "hp_unit",              "fieldtype": "Data",     "width": 80},
        
        {"label": "Efficiency",     "fieldname": "a_effeciency",         "fieldtype": "Percent",  "width": 120},
        {"label": "Actual Reading", "fieldname": "a_actual_reading",     "fieldtype": "Data",     "width": 100},

        
        {"label": "Efficiency",     "fieldname": "b_effeciency",         "fieldtype": "Percent",  "width": 120},
        {"label": "Actual Reading", "fieldname": "b_actual_reading",     "fieldtype": "Data",     "width": 100},

        
        {"label": "Efficiency",     "fieldname": "c_effeciency",         "fieldtype": "Percent",  "width": 120},
        {"label": "Actual Reading", "fieldname": "c_actual_reading",     "fieldtype": "Data",     "width": 100},
        {"label": "Meters",         "fieldname": "c_meters",             "fieldtype": "Data",     "width": 100},

        {"label": "Pick",           "fieldname": "pick",                 "fieldtype": "Data",     "width": 100},
        {"label": "Running Eff & Efficiency",     "fieldname": "stats_effeciency",     "fieldtype": "Data",  "width": 100},
        {"label": "Actual Reading", "fieldname": "stats_actual_reading", "fieldtype": "Data",     "width": 100},
        {"label": "Meters",         "fieldname": "stats_meters",         "fieldtype": "Data",     "width": 100},
    ]


def get_merged_looms_data(date):

    def safe_float(val, default=0.0):
        try:
            return float(val) if val is not None else default
        except (TypeError, ValueError):
            return default

    def fetch_shift_data(shift):
        return frappe.db.sql("""
            SELECT
                d.parent,
                d.loom,
                d.sizing_name,
                d.rpm,
                ROUND(IFNULL(d.rpm, 0) * 1.44, 2)  AS hp_unit,
                ROUND(d.effeciency, 2)               AS effeciency,
                ROUND(d.meters, 2)                   AS meters,
                ROUND(d.actual_reading, 2)           AS actual_reading,
                d.pick
            FROM `tabLoom Production Items` d
            INNER JOIN `tabLoom Production` m
                ON d.parent = m.name
            WHERE m.shift = %(shift)s
              AND m.date  = %(date)s
        """, {"shift": shift, "date": date}, as_dict=True)

    def fetch_avg_efficiency(shift):
        result = frappe.db.sql("""
            SELECT ROUND(running_average_efficiency, 2) AS average_efficiency
            FROM `tabLoom Production`
            WHERE shift = %(shift)s
              AND date  = %(date)s
            LIMIT 1
        """, {"shift": shift, "date": date}, as_dict=True)
        return result[0]["average_efficiency"] if result else ""

    def to_dict_by_loom(shift_data):
        return {str(row["loom"]): row for row in shift_data}

    def get_summary(shift_data):
        if not shift_data:
            return 0.0, 0.0
        total_meters = round(sum(safe_float(r["meters"]) for r in shift_data), 2)
        avg_eff      = round(sum(safe_float(r["effeciency"]) for r in shift_data) / len(shift_data), 2)
        return total_meters, avg_eff

    def get_combined_stats(*shifts):
        combined = [r for shift in shifts for r in shift]
        if not combined:
            return 0.0, 0.0, 0.0
        avg_eff            = round(sum(safe_float(r["effeciency"])     for r in combined) / len(combined), 0)
        sum_meters         = round(sum(safe_float(r["meters"])         for r in combined), 2)
        sum_actual_reading = round(sum(safe_float(r["actual_reading"]) for r in combined), 2)
        return avg_eff, sum_meters, sum_actual_reading

    def natural_sort_key(s):
        return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]

    def dash(color):
        return f'<b style="color:{color};text-align:center;">----</b>'

    def label(color, text):
        return f'<b style="color:{color};text-align:center;">{text}</b>'

    # ── Fetch data ────────────────────────────────────────────────────────────
    shift_a = fetch_shift_data("Shift-A")
    shift_b = fetch_shift_data("Shift-B")
    shift_c = fetch_shift_data("Shift-C")

    avg_eff_a = fetch_avg_efficiency("Shift-A")
    avg_eff_b = fetch_avg_efficiency("Shift-B")
    avg_eff_c = fetch_avg_efficiency("Shift-C")

    a_looms = to_dict_by_loom(shift_a)
    b_looms = to_dict_by_loom(shift_b)
    c_looms = to_dict_by_loom(shift_c)

    all_looms = sorted(
        set(a_looms.keys()) | set(b_looms.keys()) | set(c_looms.keys()),
        key=natural_sort_key,
    )

    merged_rows = []

    # ── Header row ────────────────────────────────────────────────────────────
    merged_rows.append({
        "a_loom":               dash("green"),
        "a_sizing_name":        dash("green"),
        "a_rpm":                dash("green"),
        "hp_unit":              label("green",  "Shift - A"),
        "a_effeciency":         label("green",  f"Avg Eff: {avg_eff_a}%") if avg_eff_a != "" else dash("green"),
        "a_actual_reading":     label("green","Shift - B"),

        "b_effeciency":         label("orange", f"Avg Eff: {avg_eff_b}%") if avg_eff_b != "" else dash("orange"),
        "b_actual_reading":     label("orange","Shift - C"),

        "c_effeciency":         label("blue",   f"Avg Eff: {avg_eff_c}%") if avg_eff_c != "" else dash("blue"),
        "c_actual_reading":     dash("blue"),
        "c_meters":             dash("blue"),

        "pick":                 dash("purple"),
        "stats_effeciency":     label("purple", f"{round(((avg_eff_a or 0) + (avg_eff_b or 0) + (avg_eff_c or 0))/3, 2)}%"),
        "stats_actual_reading": dash("purple"),
        "stats_meters":         label("purple", "STATS")
    })

    # ── Data rows ─────────────────────────────────────────────────────────────
    for loom in all_looms:
        a = a_looms.get(loom, {})
        b = b_looms.get(loom, {})
        c = c_looms.get(loom, {})

        eff_values = [safe_float(x["effeciency"]) for x in (a, b, c) if x]
        stats_eff  = round(sum(eff_values) / len(eff_values), 0) if eff_values else 0.0

        stats_m  = round(safe_float(a.get("meters")) +
                         safe_float(b.get("meters")) +
                         safe_float(c.get("meters")), 2)

        stats_ar = round(safe_float(a.get("actual_reading")) +
                         safe_float(b.get("actual_reading")) +
                         safe_float(c.get("actual_reading")), 2)

        pick           = (a.get("pick") or b.get("pick") or c.get("pick"))

        merged_rows.append({
            "parent":               a.get("parent") or b.get("parent") or c.get("parent"),

            "a_loom":               a.get("loom"),
            "a_sizing_name":        a.get("sizing_name"),
            "a_rpm":                a.get("rpm"),
            "hp_unit":              a.get("hp_unit"),
            "a_effeciency":         a.get("effeciency"),
            "a_actual_reading":     a.get("actual_reading"),

            "b_effeciency":         b.get("effeciency"),
            "b_actual_reading":     b.get("actual_reading"),

            "c_effeciency":         c.get("effeciency"),
            "c_actual_reading":     c.get("actual_reading"),
            "c_meters":             c.get("meters"),

            "pick":                 pick,
            "stats_effeciency":     stats_eff,
            "stats_actual_reading": stats_ar,
            "stats_meters":         stats_m
        })

    # ── Summary row ───────────────────────────────────────────────────────────
    a_total_meters, a_avg_eff = get_summary(shift_a)
    b_total_meters, b_avg_eff = get_summary(shift_b)
    c_total_meters, c_avg_eff = get_summary(shift_c)

    stats_avg_eff, stats_meters, stats_actual_reading = \
        get_combined_stats(shift_a, shift_b, shift_c)

    merged_rows.append({
        "parent":               "",
        "a_loom":               "",
        "a_sizing_name":        '<b style="color:black;">Total / Average</b>',
        "a_rpm":                "",
        "hp_unit":              "",
        "a_effeciency":         f'<b style="color:green;">Avg: {a_avg_eff}</b>',
        "a_actual_reading":     "",
        "b_effeciency":         f'<b style="color:orange;">Avg: {b_avg_eff}</b>',
        "b_actual_reading":     "",

        "c_effeciency":         f'<b style="color:blue;">Avg: {c_avg_eff}</b>',
        "c_actual_reading":     "",
        "c_meters":             f'<b style="color:blue;">Total: {c_total_meters}</b>',

        "pick":                 "",
        "stats_effeciency":     f'<b style="color:purple;">Avg: {stats_avg_eff}</b>',
        "stats_actual_reading": f'<b style="color:purple;">Total: {stats_actual_reading}</b>',
        "stats_meters":         f'<b style="color:purple;">Total: {stats_meters}</b>'
    })

    return merged_rows