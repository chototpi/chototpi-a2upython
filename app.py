from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from pi_python import PiNetwork
import os, traceback, time, requests
import json
import mysql.connector

def get_db_connection():
    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        port=int(os.getenv("DB_PORT", 3306))
    )
    return conn
load_dotenv()

app = Flask(__name__)
CORS(app, origins=["https://testnet.chototpi.site"], supports_credentials=True)

# 🔐 Khởi tạo SDK Pi A2U
pi = PiNetwork()
pi.initialize(
    api_key=os.getenv("PI_API_KEY"),
    wallet_private_key=os.getenv("APP_PRIVATE_KEY"),
    env=os.getenv("PI_ENV", "testnet")
)

# ---------- SQLite DB ----------
DB_FILE = os.getenv("A2U_DB_FILE", "payments.db")

def get_db_connection():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def save_payment(payment_id, identifier, uid, amount, status, raw_response):
    conn = get_db_connection()
    cur = conn.cursor()
    now = int(time.time())
    cur.execute("""
        INSERT OR REPLACE INTO payment_data(payment_id, identifier, uid, amount, status, created_at, updated_at, raw_response)
        VALUES (?, ?, ?, ?, ?, COALESCE((SELECT created_at FROM payments WHERE payment_id = ?), ?), ?, ?)
    """, (payment_id, identifier, uid, amount, status, payment_id, now, now, json.dumps(raw_response)))
    conn.commit()
    conn.close()

def update_payment_txid(payment_id, txid, status="submitted"):
    conn = get_db_connection()
    cur = conn.cursor()
    now = int(time.time())
    cur.execute("UPDATE payments SET txid = ?, status = ?, updated_at = ? WHERE payment_id = ?", (txid, status, now, payment_id))
    conn.commit()
    conn.close()

def update_payment_status(payment_id, status, raw_response=None):
    conn = get_db_connection()
    cur = conn.cursor()
    now = int(time.time())
    cur.execute("UPDATE payments SET status = ?, updated_at = ?, raw_response = ? WHERE payment_id = ?",
                (status, now, json.dumps(raw_response) if raw_response else None, payment_id))
    conn.commit()
    conn.close()

def get_payment_record(payment_id):
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM payments WHERE payment_id = ?", (payment_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

# init DB at startup
init_db()

# ---------- Endpoints ----------
@app.route("/", methods=["GET"])
def home():
    return "✅ Pi A2U Python backend is running."

# STEP 1: Verify user
@app.route("/api/verify-user", methods=["POST"])
def verify_user():
    try:
        data = request.get_json()
        access_token = data.get("accessToken")
        if not access_token:
            return jsonify({"error": "Thiếu accessToken"}), 400

        headers = {"Authorization": f"Bearer {access_token}"}
        url = "https://api.minepi.com/v2/me"
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            return jsonify({"error": "User không hợp lệ", "detail": response.text}), 401

        return jsonify({"success": True, "user": response.json()})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# STEP 2 + 3: Create payment
@app.route("/api/create-payment", methods=["POST"])
def api_create_payment():
    try:
        payload = request.get_json() or {}
        uid = payload.get("uid") or payload.get("user_uid")
        amount = payload.get("amount")
        metadata = payload.get("metadata", {})

        if not uid or not amount:
            return jsonify({"success": False, "message": "Thiếu uid hoặc amount"}), 400

        identifier = f"a2u-{uid[:6]}-{int(time.time())}"
        payment_data = {
            "amount": str(amount),
            "memo": identifier,
            "metadata": metadata,
            "uid": uid,
            "user_uid": uid,
            "identifier": identifier,
            "from_address": pi.keypair.public_key,
            "network": pi.env if hasattr(pi, "env") else "testnet"
        }

        payment_id = pi.create_payment(payment_data)
        if not payment_id:
            return jsonify({"success": False, "message": "create_payment trả về rỗng"}), 500

        save_payment(payment_id, identifier, uid, str(amount), "pending", payment_data)
        return jsonify({"success": True, "payment_id": payment_id, "identifier": identifier})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500

# STEP 4 + 5: Submit payment (gửi txid vào blockchain)
@app.route("/api/submit-payment", methods=["POST"])
def api_submit_payment():
    try:
        data = request.get_json() or {}
        payment_id = data.get("payment_id")
        if not payment_id:
            return jsonify({"success": False, "message": "Thiếu payment_id"}), 400

        txid = pi.submit_payment(payment_id, False)
        if not txid:
            return jsonify({"success": False, "message": "submit_payment thất bại"}), 500

        update_payment_txid(payment_id, txid, status="submitted")
        return jsonify({"success": True, "payment_id": payment_id, "txid": txid})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500

# STEP 6: Complete payment
@app.route("/api/complete-payment", methods=["POST"])
def api_complete_payment():
    try:
        data = request.get_json() or {}
        payment_id = data.get("payment_id")
        txid = data.get("txid")
        if not payment_id or not txid:
            return jsonify({"success": False, "message": "Thiếu payment_id hoặc txid"}), 400

        payment = pi.complete_payment(payment_id, txid)
        if not payment:
            return jsonify({"success": False, "message": "complete_payment thất bại"}), 500

        update_payment_status(payment_id, "completed", payment)
        return jsonify({"success": True, "payment": payment})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500

# DEBUG: Xem record payment
@app.route("/api/payment/<payment_id>", methods=["GET"])
def api_get_payment(payment_id):
    try:
        rec = get_payment_record(payment_id)
        if not rec:
            return jsonify({"success": False, "message": "Không tìm thấy payment"}), 404
        try:
            rec['raw_response'] = json.loads(rec.get('raw_response') or "{}")
        except:
            pass
        return jsonify({"success": True, "payment": rec})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
