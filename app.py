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

# ✅ Use ENV variable (for Render)
creds_dict = json.loads(os.environ["GOOGLE_CREDENTIALS"])

creds = ServiceAccountCredentials.from_json_keyfile_dict(
    creds_dict, scope
)

client = gspread.authorize(creds)

# ✅ Your Sheet + Worksheet
sheet = client.open("AKASHAVANI").worksheet("EmpDB")


# ✅ GET DATA
@app.route("/get-data", methods=["GET"])
def get_data():
    return jsonify(sheet.get_all_records())


# ✅ ADD DATA
@app.route("/add-data", methods=["POST"])
def add_data():
    data = request.json

    sheet.append_row([
        data.get("ID", ""),
        data.get("Name", ""),
        data.get("Basic", "")
    ])

    return {"status": "success"}


# ✅ RUN SERVER (Render compatible)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)