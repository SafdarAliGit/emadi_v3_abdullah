import frappe
import re

def execute(filters=None):
    if not filters:
        filters = {}

    start_date = filters.get("start_date")
    end_date = filters.get("end_date")

    if not start_date or not end_date:
        frappe.throw("Please select Start Date and End Date")

    data = get_merged_looms_data(start_date, end_date)
    columns = get_columns()

    return columns, data


def get_columns():
    return [
        # Shift A columns
        {"label": "Loom",          "fieldname": "a_loom",            "fieldtype": "Data", "width": 120},
        {"label": "Quality Name",  "fieldname": "a_sizing_name",     "fieldtype": "Data", "width": 140},
        {"label": "Actual Reading","fieldname": "a_actual_reading",  "fieldtype": "Data", "width": 100},
        {"label": "Efficiency",    "fieldname": "a_effeciency",      "fieldtype": "Data", "width": 100},

        # Shift B columns
        {"label": "Actual Reading","fieldname": "b_actual_reading",  "fieldtype": "Data", "width": 100},
        {"label": "Efficiency",    "fieldname": "b_effeciency",      "fieldtype": "Data", "width": 100},

        # Shift C columns
        {"label": "Actual Reading","fieldname": "c_actual_reading",  "fieldtype": "Data", "width": 100},
        {"label": "Efficiency",    "fieldname": "c_effeciency",      "fieldtype": "Data", "width": 100},

        # Stats columns
        {"label": "Actual Reading","fieldname": "stats_actual_reading",  "fieldtype": "Data", "width": 100},
        {"label": "Meters",        "fieldname": "stats_meters",          "fieldtype": "Data", "width": 100},
          {"label": "Efficiency",    "fieldname": "stats_effeciency",      "fieldtype": "Data", "width": 100},
    ]


def get_merged_looms_data(start_date, end_date):

    def fetch_shift_data(shift):
        return frappe.db.sql("""
            SELECT d.parent, d.loom, d.sizing_name, d.rpm,
                   ROUND(d.effeciency, 2)     AS effeciency,
                   ROUND(d.meters, 2)         AS meters,
                   ROUND(d.actual_reading, 2) AS actual_reading
            FROM `tabLoom Production Items` d
            JOIN `tabLoom Production` m ON d.parent = m.name
            WHERE m.shift = %(shift)s
              AND m.date BETWEEN %(start_date)s AND %(end_date)s
        """, {"shift": shift, "start_date": start_date, "end_date": end_date}, as_dict=True)

    def safe_float(val):
        try:
            return float(val)
        except (TypeError, ValueError):
            return 0.0

    # Aggregate duplicate loom entries within the same shift:
    # meters & actual_reading are summed; efficiency is averaged.
    def to_dict_by_loom(shift_data):
        result = {}
        counts = {}
        for row in shift_data:
            key = str(row['loom'])
            if key in result:
                existing = result[key]
                existing['meters']         = safe_float(existing.get('meters'))         + safe_float(row.get('meters'))
                existing['actual_reading'] = safe_float(existing.get('actual_reading')) + safe_float(row.get('actual_reading'))
                existing['effeciency']     = safe_float(existing.get('effeciency'))     + safe_float(row.get('effeciency'))
                counts[key] += 1
            else:
                result[key] = dict(row)
                counts[key] = 1
        # Finalise averaged efficiency
        for key in result:
            result[key]['effeciency'] = round(result[key]['effeciency'] / counts[key], 2)
        return result

    def natural_sort_key(s):
        return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', s)]

    shift_a = fetch_shift_data("Shift-A")
    shift_b = fetch_shift_data("Shift-B")
    shift_c = fetch_shift_data("Shift-C")

    a_looms = to_dict_by_loom(shift_a)
    b_looms = to_dict_by_loom(shift_b)
    c_looms = to_dict_by_loom(shift_c)

    all_looms = sorted(
        set(a_looms.keys()) | set(b_looms.keys()) | set(c_looms.keys()),
        key=natural_sort_key
    )

    merged_rows = []

    # ── Header row ────────────────────────────────────────────────────────────
    merged_rows.append({
        'parent':              '',
        'a_loom':              '<b style="color:green;">----</b>',
        'a_sizing_name':       '<b style="color:green;">----</b>',
        'a_actual_reading':    '<b style="color:green;">Shift - A</b>',
        'a_effeciency':        '<b style="color:green;">Shift - A</b>',
        'b_actual_reading':    '<b style="color:orange;">Shift - B</b>',
        'b_effeciency':        '<b style="color:orange;">Shift - B</b>',
        'c_actual_reading':    '<b style="color:blue;">Shift - C</b>',
        'c_effeciency':        '<b style="color:blue;">Shift - C</b>',
        
       
        'stats_actual_reading':'<b style="color:purple;">STATS</b>',
         'stats_effeciency':    '<b style="color:purple;">----</b>',
        'stats_meters':        '<b style="color:purple;">----</b>',
    })

    # ── Data rows ─────────────────────────────────────────────────────────────
    for loom in all_looms:
        a = a_looms.get(loom)
        b = b_looms.get(loom)
        c = c_looms.get(loom)

        # Use None to distinguish "loom not present in this shift" from 0
        a_eff = safe_float(a.get('effeciency')) if a else None
        b_eff = safe_float(b.get('effeciency')) if b else None
        c_eff = safe_float(c.get('effeciency')) if c else None

        # Average only across shifts that have data for this loom
        present_effs = [e for e in [a_eff, b_eff, c_eff] if e is not None]
        stats_eff = round(sum(present_effs) / len(present_effs), 0) if present_effs else 0

        stats_meters = round(
            safe_float(a.get('meters') if a else 0) +
            safe_float(b.get('meters') if b else 0) +
            safe_float(c.get('meters') if c else 0),
            2
        )
        stats_actual = round(
            safe_float(a.get('actual_reading') if a else 0) +
            safe_float(b.get('actual_reading') if b else 0) +
            safe_float(c.get('actual_reading') if c else 0),
            2
        )

        merged_rows.append({
            'parent': (
                (a or {}).get('parent') or
                (b or {}).get('parent') or
                (c or {}).get('parent')
            ),
            'a_loom':              (a or {}).get('loom'),
            'a_sizing_name':       (a or {}).get('sizing_name'),
            'a_effeciency':        f"{a_eff}%" if a_eff is not None else '—',
            'a_actual_reading':    (a or {}).get('actual_reading'),

            'b_effeciency':        f"{b_eff}%" if b_eff is not None else '—',
            'b_actual_reading':    (b or {}).get('actual_reading'),

            'c_effeciency':        f"{c_eff}%" if c_eff is not None else '—',
            'c_actual_reading':    (c or {}).get('actual_reading'),

            'stats_effeciency':    f"{stats_eff}%",
            'stats_meters':        stats_meters,
            'stats_actual_reading':stats_actual,
        })

    # ── Summary row — derived from the data rows above so totals match exactly ─
    data_rows = merged_rows[1:]  # exclude header row

    def collect_eff(key):
        vals = []
        for r in data_rows:
            raw = r.get(key, '')
            if raw and raw != '—':
                try:
                    vals.append(float(str(raw).replace('%', '').strip()))
                except (TypeError, ValueError):
                    pass
        return vals

    a_eff_vals   = collect_eff('a_effeciency')
    b_eff_vals   = collect_eff('b_effeciency')
    c_eff_vals   = collect_eff('c_effeciency')
    all_eff_vals = a_eff_vals + b_eff_vals + c_eff_vals

    a_avg_eff     = round(sum(a_eff_vals)   / len(a_eff_vals),   2) if a_eff_vals   else 0
    b_avg_eff     = round(sum(b_eff_vals)   / len(b_eff_vals),   2) if b_eff_vals   else 0
    c_avg_eff     = round(sum(c_eff_vals)   / len(c_eff_vals),   2) if c_eff_vals   else 0
    stats_avg_eff = round(sum(all_eff_vals) / len(all_eff_vals), 0) if all_eff_vals else 0

    total_meters = round(sum(safe_float(r.get('stats_meters'))         for r in data_rows), 2)
    total_actual = round(sum(safe_float(r.get('stats_actual_reading')) for r in data_rows), 2)

    merged_rows.append({
        'parent':              '',
        'a_loom':              '',
        'a_sizing_name':       '<b style="color:black;">Total / Average</b>',
        'a_effeciency':        f'<b style="color:green;">Avg: {a_avg_eff}%</b>',
        'b_effeciency':        f'<b style="color:orange;">Avg: {b_avg_eff}%</b>',
        'c_effeciency':        f'<b style="color:blue;">Avg: {c_avg_eff}%</b>',
        'stats_effeciency':    f'<b style="color:purple;">Avg: {stats_avg_eff}%</b>',
        'stats_meters':        f'<b style="color:purple;">Total: {total_meters}</b>',
        'stats_actual_reading':f'<b style="color:purple;">Total: {total_actual}</b>',
    })

    return merged_rows