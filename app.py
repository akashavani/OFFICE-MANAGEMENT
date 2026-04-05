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

        # 🔍 Column indexes
        month_idx = headers.index("Salary Month")
        station_idx = headers.index("Pay Drawn Station")
        emp_idx = headers.index("Employee Name")

        # Optional
        category_idx = headers.index("Category") if "Category" in headers else -1

        def clean(val):
            return str(val).strip().lower()

        # ⚡ Create lookup map
        row_map = {}
        for i, r in enumerate(rows):
            key = f"{clean(r[month_idx])}|{clean(r[station_idx])}|{clean(r[emp_idx])}"
            
            if category_idx >= 0:
                key += f"|{clean(r[category_idx])}"

            row_map[key] = i + 2

        updates = []
        update_cells = []
        new_rows = []

        # 🔄 Process incoming
        for row_obj in edit_rows:

            key = f"{clean(row_obj.get('Salary Month'))}|{clean(row_obj.get('Pay Drawn Station'))}|{clean(row_obj.get('Employee Name'))}"

            if category_idx >= 0:
                key += f"|{clean(row_obj.get('Category'))}"

            new_row = [row_obj.get(h, "") for h in headers]

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
    
    # =========================
# RUN SERVER
# =========================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
