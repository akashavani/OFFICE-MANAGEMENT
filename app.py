from flask import Flask, request, jsonify
from flask_cors import CORS
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json

app = Flask(__name__)
CORS(app)

# Google Sheets scope
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

# ENV credentials
creds_dict = json.loads(os.environ["GOOGLE_CREDENTIALS"])

creds = ServiceAccountCredentials.from_json_keyfile_dict(
    creds_dict, scope
)

client = gspread.authorize(creds)

# ✅ OPEN ALL SHEETS PROPERLY
spreadsheet = client.open("AKASHAVANI")

emp_sheet = spreadsheet.worksheet("EmpDB")
sbg_sheet = spreadsheet.worksheet("BudgetDB")
sbgexp_sheet = spreadsheet.worksheet("SBGexpenditure")
pb_sheet = spreadsheet.worksheet("PBDB")
cpc_sheet = spreadsheet.worksheet("CPC7DB")
city_sheet = spreadsheet.worksheet("CityZoneDB")
qtrs_sheet = spreadsheet.worksheet("QtrsRateDB")
comm_sheet = spreadsheet.worksheet("CommFactDB")
it_sheet = spreadsheet.worksheet("ITDB")


# =========================
# API ROUTES
# =========================

def sheet_to_json(sheet):
    data = sheet.get_all_values()

    headers = data[0]   # first row
    rows = data[1:]     # rest rows

    return {
        "headers": headers,
        "rows": rows
    }


@app.route("/emp", methods=["GET"])
def get_emp():
    return jsonify(sheet_to_json(emp_sheet))


@app.route("/sbg", methods=["GET"])
def get_sbg():
    return jsonify(sheet_to_json(sbg_sheet))


@app.route("/sbgexp", methods=["GET"])
def get_sbgexp():
    return jsonify(sheet_to_json(sbgexp_sheet))


@app.route("/pb", methods=["GET"])
def get_pb():
    return jsonify(sheet_to_json(pb_sheet))


@app.route("/cpc", methods=["GET"])
def get_cpc():
    return jsonify(sheet_to_json(cpc_sheet))


@app.route("/city", methods=["GET"])
def get_city():
    return jsonify(sheet_to_json(city_sheet))


@app.route("/qtrs", methods=["GET"])
def get_qtrs():
    return jsonify(sheet_to_json(qtrs_sheet))


@app.route("/comm", methods=["GET"])
def get_comm():
    return jsonify(sheet_to_json(comm_sheet))


@app.route("/it", methods=["GET"])
def get_it():
    return jsonify(sheet_to_json(it_sheet))



@app.route("/pb/update", methods=["POST"])
def update_pb():
    try:
        req_data = request.get_json()
        edit_rows = req_data.get("data", [])

        if not edit_rows:
            return jsonify({"status": "error", "message": "No data received"}), 400

        # 📥 Existing data
        data = pb_sheet.get_all_values()
        headers = data[0]
        rows = data[1:]
        print("📌 HEADERS:", headers)
        # 🔍 Column indexes
        month_idx = headers.index("Salary Month")
        station_idx = headers.index("Pay Drawn Station")
        emp_idx = headers.index("Employee Name")
        hris_idx = headers.index("HRIS") if "HRIS" in headers else -1

        # Optional
        category_idx = headers.index("Category") if "Category" in headers else -1

        def clean(val):
            return str(val).strip().lower()

        # ⚡ Create lookup map
        row_map = {}
        for i, r in enumerate(rows):
            key = f"{clean(r[month_idx])}|{clean(r[station_idx])}|{clean(r[emp_idx])}"

            if hris_idx >= 0:
                key += f"|{clean(r[hris_idx])}"
            
            if category_idx >= 0:
                key += f"|{clean(r[category_idx])}"

            row_map[key] = i + 2

        updates = []
        update_cells = []
        new_rows = []

        # 🔄 Process incoming
        for row_obj in edit_rows:
            print("📦 Incoming Row:", row_obj)
            key = f"{clean(row_obj.get('Salary Month'))}|{clean(row_obj.get('Pay Drawn Station'))}|{clean(row_obj.get('Employee Name'))}"

            if hris_idx >= 0:
                key += f"|{clean(row_obj.get('HRIS'))}"

            if category_idx >= 0:
                key += f"|{clean(row_obj.get('Category'))}"

            new_row = []

            for i, h in enumerate(headers):

                val = row_obj.get(h, "")

                # 🔥 ONLY protect designation column
                if h.strip().lower() == "designation on salary month":
                    if not val and key in row_map:
                        existing_row = rows[row_map[key] - 2]
                        val = existing_row[i]

                new_row.append(val)
            print("📊 Generated Row:", new_row)

            if key in row_map:
                row_num = row_map[key]

                # batch update preparation
                for col_idx, val in enumerate(new_row):
                    update_cells.append({
                        "range": gspread.utils.rowcol_to_a1(row_num, col_idx+1),
                        "values": [[val]]
                    })
                updates.append(row_num)

            else:
                new_rows.append(new_row)
                

        # ⚡ BULK UPDATE (FAST)
        if update_cells:
            pb_sheet.batch_update(update_cells)

        # ➕ Append
        if new_rows:
            pb_sheet.append_rows(new_rows)

        return jsonify({
            "status": "success",
            "updated": len(updates),
            "added": len(new_rows)
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    
    
@app.route("/sbgexp/update", methods=["POST"])
def update_sbgexp():
    try:
        import re
        from datetime import datetime
        import gspread

        req_data = request.get_json()
        edit_rows = req_data.get("data", [])
        mode = req_data.get("mode", "replace")  # 🔥 flexible

        if not edit_rows:
            return jsonify({"status": "error", "message": "No data received"}), 400

        # =========================
        # 🔥 FIXED HEADERS
        # =========================
        headers = [
            "Date",
            "Station",
            "Bill / Invoice Details",
            "SBG Expenditure Under",
            "Expenditure Details",
            "Expenditure Amount (₹ in 000)",
            "Cumulative Sum of Expenditure (₹ in 000)"
        ]

        # =========================
        # 🔧 HELPERS
        # =========================
        def clean(val):
            return str(val).strip().lower()

        def normalize_date(val):
            try:
                return datetime.strptime(val.strip(), "%d-%m-%Y").strftime("%Y-%m-%d")
            except:
                return clean(val)

        def clean_details(val):
            if not val:
                return ""
            val = str(val).lower()
            val = re.sub(r"\(.*?\)", "", val)  # 🔥 remove dynamic breakup
            return re.sub(r"\s+", " ", val).strip()

        def make_key(row):
            return f"{normalize_date(row.get('Date',''))}|{clean(row.get('Station',''))}|{clean(row.get('SBG Expenditure Under',''))}|{clean_details(row.get('Expenditure Details',''))}"

        # =========================
        # 🔥 CLEAN INPUT (CRITICAL)
        # =========================
        cleaned_rows = []

        for row in edit_rows:
            date_val = str(row.get("Date", "")).strip()

            if not date_val or date_val.lower() == "date":
                continue

            if not row.get("Station") or not row.get("SBG Expenditure Under"):
                continue

            cleaned_rows.append(row)

        edit_rows = cleaned_rows

        # =========================
        # 🔥 REPLACE MODE (SAFE RESET)
        # =========================
        if mode == "replace":

            sbgexp_sheet.clear()
            sbgexp_sheet.append_row(headers)

            seen = set()
            final_rows = []

            for row_obj in edit_rows:
                key = make_key(row_obj)

                if key in seen:
                    continue
                seen.add(key)

                final_rows.append([row_obj.get(h, "") for h in headers])

            if final_rows:
                sbgexp_sheet.append_rows(final_rows)

            return jsonify({
                "status": "success",
                "mode": "replace",
                "added": len(final_rows)
            })

        # =========================
        # 🔥 UPDATE MODE (FUTURE USE)
        # =========================
        data = sbgexp_sheet.get_all_values()

        if not data:
            sbgexp_sheet.append_row(headers)
            existing_rows = []
        else:
            existing_rows = data[1:]

        # build existing map
        row_map = {}
        for i, r in enumerate(existing_rows):
            existing_row = {
                "Date": r[0],
                "Station": r[1],
                "SBG Expenditure Under": r[3],
                "Expenditure Details": r[4],
            }
            key = make_key(existing_row)
            row_map[key] = i + 2

        update_cells = []
        new_rows = []
        seen_keys = set()

        for row_obj in edit_rows:

            key = make_key(row_obj)

            if key in seen_keys:
                continue
            seen_keys.add(key)

            new_row = [row_obj.get(h, "") for h in headers]

            # 🔁 UPDATE EXISTING
            if key in row_map:
                row_num = row_map[key]

                for col_idx, val in enumerate(new_row):
                    update_cells.append({
                        "range": gspread.utils.rowcol_to_a1(row_num, col_idx + 1),
                        "values": [[val]]
                    })

            # ➕ ADD NEW
            else:
                new_rows.append(new_row)

        if update_cells:
            sbgexp_sheet.batch_update(update_cells)

        if new_rows:
            sbgexp_sheet.append_rows(new_rows)

        return jsonify({
            "status": "success",
            "mode": "update",
            "updated": len(update_cells),
            "added": len(new_rows)
        })

    except Exception as e:
        print("❌ ERROR:", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500
    

@app.route("/sbg/bulk-update", methods=["POST"])
def bulk_update_sbg():
    try:
        req = request.get_json()
        rows = req.get("rows", [])

        if not rows:
            return jsonify({"status": "error", "message": "No rows"}), 400

        # 📥 Read existing sheet
        existing_data = sbg_sheet.get_all_values()
        total_cols = len(existing_data[0])

        # ✅ Convert column number → Excel letter (AA, AB...)
        def col_to_letter(n):
            result = ""
            while n > 0:
                n, rem = divmod(n - 1, 26)
                result = chr(65 + rem) + result
            return result

        end_col = col_to_letter(total_cols)
        total_rows = len(rows)

        print("🔥 API HIT")
        print("🔥 Rows received:", total_rows)
        print("🔥 Sample row:", rows[0])

        # ✅ Ensure row length matches sheet
        rows = [r[:total_cols] for r in rows]

        # ✅ Correct range (DATA starts from row 3)
        range_name = f"A3:{end_col}{total_rows + 2}"

        print("📊 Updating Range:", range_name)

        # 🔥 BULK UPDATE
        sbg_sheet.batch_update([{
            "range": range_name,
            "values": rows
        }])

        return jsonify({
            "status": "success",
            "updated_rows": total_rows
        })

    except Exception as e:
        print("❌ ERROR:", str(e))
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    
    # =========================
# RUN SERVER
# =========================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
