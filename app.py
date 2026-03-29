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
pb_sheet = spreadsheet.worksheet("PBDB")
cpc_sheet = spreadsheet.worksheet("CPC7DB")
city_sheet = spreadsheet.worksheet("CityZoneDB")
qtrs_sheet = spreadsheet.worksheet("QtrsRateDB")
comm_sheet = spreadsheet.worksheet("CommFactDB")
it_sheet = spreadsheet.worksheet("ITDB")


# =========================
# API ROUTES
# =========================

@app.route("/emp", methods=["GET"])
def get_emp():
    return jsonify(emp_sheet.get_all_records())


@app.route("/pb", methods=["GET"])
def get_pb():
    return jsonify(pb_sheet.get_all_records())


@app.route("/cpc", methods=["GET"])
def get_cpc():
    return jsonify(cpc_sheet.get_all_records())


@app.route("/city", methods=["GET"])
def get_city():
    return jsonify(city_sheet.get_all_records())


@app.route("/qtrs", methods=["GET"])
def get_qtrs():
    return jsonify(qtrs_sheet.get_all_records())


@app.route("/comm", methods=["GET"])
def get_comm():
    return jsonify(comm_sheet.get_all_records())


@app.route("/it", methods=["GET"])
def get_it():
    return jsonify(it_sheet.get_all_records())


# =========================
# RUN SERVER
# =========================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
