# app.py (phần cập nhật: create_payment + sqlite storage)
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from pi_python import PiNetwork
import os, traceback, time, requests
import sqlite3
import json

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

# ---------- SQLite DB (rất nhẹ cho step dev/test) ----------
DB_FILE = os.getenv("A2U_DB_FILE", "payments.db")

def get_db_connection():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        payment_id TEXT UNIQUE,
        identifier TEXT,
        uid TEXT,
        amount TEXT,
        status TEXT,
        txid TEXT,
        created_at INTEGER,
        updated_at INTEGER,
        raw_response TEXT
    );
    """)
    conn.commit()
    conn.close()

def save_payment(payment_id, identifier, uid, amount, status, raw_response):
    conn = get_db_connection()
    cur = conn.cursor()
    now = int(time.time())
    # INSERT OR IGNORE để tránh duplicate nếu trước đó đã có
    cur.execute("""
        INSERT OR REPLACE INTO payments(payment_id, identifier, uid, amount, status, created_at, updated_at, raw_response)
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

def get_payment_record(payment_id):
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM payments WHERE payment_id = ?", (payment_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

# init DB at startup
init_db()

# ---------- Existing endpoints (kept minimal) ----------
@app.route("/", methods=["GET"])
def home():
    return "✅ Pi A2U Python backend is running."

@app.route("/api/verify-user", methods=["POST"])
def verify_user():
    try:
        data = request.get_json()
        access_token = data.get("accessToken")
        if not access_token:
            return jsonify({"error": "Thiếu accessToken"}), 400

        headers = {"Authorization": f"Bearer {access_token}"}
        # verify on mainnet/testnet according to your env - here we call /me
        url = "https://api.minepi.com/v2/me"
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            return jsonify({"error": "User không hợp lệ", "detail": response.text}), 401

        user_data = response.json()
        return jsonify({"success": True, "user": user_data})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ---------- NEW: create-payment (BƯỚC 2) ----------
@app.route("/api/create-payment", methods=["POST"])
def api_create_payment():
    """
    Input JSON:
    {
      "uid": "<user-uid-from-frontend>",
      "amount": "1.5",             # string or number
      "metadata": { ... }          # optional
    }

    Output:
    {
      "success": True,
      "payment_id": "...",
      "identifier": "a2u-test-..."
    }
    """
    try:
        payload = request.get_json() or {}
        uid = payload.get("uid") or payload.get("user_uid")
        amount = payload.get("amount")
        metadata = payload.get("metadata", {})

        if not uid or not amount:
            return jsonify({"success": False, "message": "Thiếu uid hoặc amount"}), 400

        # Tạo identifier duy nhất (dùng để memo / map nhanh)
        identifier = f"a2u-{uid[:6]}-{int(time.time())}"

        payment_data = {
            "amount": str(amount),
            "memo": identifier,
            "metadata": metadata,
            # Pi SDK docs may accept 'uid' or 'user_uid' -> include both to be safe
            "uid": uid,
            "user_uid": uid,
            "identifier": identifier,
            # from_address is normally app public key (SDK may fill automatically)
            "from_address": pi.keypair.public_key,
            "network": pi.env if hasattr(pi, "env") else "testnet"
        }

        # Gọi SDK -> create payment (Pi server sẽ ánh xạ uid -> user wallet (to_address) cho bạn)
        payment_id = pi.create_payment(payment_data)

        if not payment_id:
            return jsonify({"success": False, "message": "create_payment trả về rỗng"}), 500

        # Lưu payment_id vào DB với trạng thái pending
        save_payment(payment_id, identifier, uid, str(amount), "pending", payment_data)

        return jsonify({"success": True, "payment_id": payment_id, "identifier": identifier})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500

# ---------- DEBUG: xem record payment đã lưu ----------
@app.route("/api/payment/<payment_id>", methods=["GET"])
def api_get_payment(payment_id):
    try:
        rec = get_payment_record(payment_id)
        if not rec:
            return jsonify({"success": False, "message": "Không tìm thấy payment"}), 404
        # parse raw_response back to JSON if possible
        try:
            rec['raw_response'] = json.loads(rec.get('raw_response') or "{}")
        except:
            pass
        return jsonify({"success": True, "payment": rec})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500

# ---------- (Lưu ý) phần submit/complete sẽ là bước tiếp theo ----------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
