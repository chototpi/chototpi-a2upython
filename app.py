# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from pi_python import PiNetwork
import os, traceback, time, requests
import json
import mysql.connector

# load env first
load_dotenv()

app = Flask(__name__)
CORS(app, origins=["https://testnet.chototpi.site"], supports_credentials=True)

# ---------------- MySQL connection helper ----------------
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "chototpi"),
        port=int(os.getenv("DB_PORT", 3306)),
        autocommit=False
    )

# ---------------- Init Pi SDK ----------------
pi = PiNetwork()
pi.initialize(
    api_key=os.getenv("PI_API_KEY"),
    wallet_private_key=os.getenv("APP_PRIVATE_KEY"),
    env=os.getenv("PI_ENV", "testnet")
)

# ---------------- DB init (create payments table if not exists) ----------------
def init_db():
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INT PRIMARY KEY AUTO_INCREMENT,
            payment_id VARCHAR(255) UNIQUE,
            identifier VARCHAR(255),
            uid VARCHAR(255),
            amount DECIMAL(36,18),
            status VARCHAR(50),
            txid VARCHAR(255),
            created_at BIGINT,
            updated_at BIGINT,
            raw_response LONGTEXT
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        conn.commit()
        cur.close()
    except Exception as e:
        print("init_db error:", e)
    finally:
        if conn:
            conn.close()

# ---------------- DB helpers ----------------
def save_payment(payment_id, identifier, uid, amount, status, raw_response):
    """
    Insert new payment or keep existing created_at if present.
    Uses ON DUPLICATE KEY UPDATE to avoid double-insert.
    """
    conn = None
    try:
        now = int(time.time())
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO payments(payment_id, identifier, uid, amount, status, created_at, updated_at, raw_response)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                identifier = VALUES(identifier),
                uid = VALUES(uid),
                amount = VALUES(amount),
                status = VALUES(status),
                updated_at = VALUES(updated_at),
                raw_response = VALUES(raw_response)
        """, (payment_id, identifier, uid, amount, status, now, now, json.dumps(raw_response)))
        conn.commit()
        cur.close()
    except Exception as e:
        if conn:
            conn.rollback()
        print("save_payment error:", e)
        raise
    finally:
        if conn:
            conn.close()
            def update_payment_txid(payment_id, txid, status="submitted"):
    conn = None
    try:
        now = int(time.time())
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE payments SET txid=%s, status=%s, updated_at=%s WHERE payment_id=%s",
                    (txid, status, now, payment_id))
        conn.commit()
        cur.close()
    except Exception as e:
        if conn:
            conn.rollback()
        print("update_payment_txid error:", e)
        raise
    finally:
        if conn:
            conn.close()

def update_payment_status(payment_id, status, raw_response=None):
    conn = None
    try:
        now = int(time.time())
        conn = get_db_connection()
        cur = conn.cursor()
        if raw_response is not None:
            raw_json = json.dumps(raw_response)
            cur.execute("UPDATE payments SET status=%s, updated_at=%s, raw_response=%s WHERE payment_id=%s",
                        (status, now, raw_json, payment_id))
        else:
            cur.execute("UPDATE payments SET status=%s, updated_at=%s WHERE payment_id=%s",
                        (status, now, payment_id))
        conn.commit()
        cur.close()
    except Exception as e:
        if conn:
            conn.rollback()
        print("update_payment_status error:", e)
        raise
    finally:
        if conn:
            conn.close()

def get_payment_record(payment_id):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM payments WHERE payment_id = %s", (payment_id,))
        row = cur.fetchone()
        cur.close()
        return row
    except Exception as e:
        print("get_payment_record error:", e)
        return None
    finally:
        if conn:
            conn.close()

# init DB (safe even if table exists)
init_db()

# ---------------- Endpoints (6-step A2U) ----------------
@app.route("/", methods=["GET"])
def home():
    return "✅ Pi A2U Testnet backend (MySQL) is running."

# STEP 1: Verify user (from frontend accessToken)
@app.route("/api/verify-user", methods=["POST"])
def verify_user():
    try:
        data = request.get_json() or {}
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

# STEP 2 + 3: Create payment and save payment_id (pending)
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

        # Save into MySQL
        save_payment(payment_id, identifier, uid, str(amount), "pending", payment_data)
        return jsonify({"success": True, "payment_id": payment_id, "identifier": identifier})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500

# STEP 4 + 5: Submit payment -> get txid and save it
@app.route("/api/submit-payment", methods=["POST"])
def api_submit_payment():
    try:
        data = request.get_json() or {}
        payment_id = data.get("payment_id")
        if not payment_id:
            return jsonify({"success": False, "message": "Thiếu payment_id"}), 400

        txid = pi.submit_payment(payment_id, False)
        if not txid:
            return jsonify({"success": False, "message": "submit_payment thất bại (empty txid)"}), 500

        update_payment_txid(payment_id, txid, status="submitted")
        return jsonify({"success": True, "payment_id": payment_id, "txid": txid})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500

# STEP 6: Complete payment -> finalise and update status
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

# DEBUG: get record
@app.route("/api/payment/<payment_id>", methods=["GET"])
def api_get_payment(payment_id):
    try:
        rec = get_payment_record(payment_id)
        if not rec:
            return jsonify({"success": False, "message": "Không tìm thấy payment"}), 404
        # parse raw_response if possible
        try:
            if rec.get("raw_response"):
                rec["raw_response"] = json.loads(rec["raw_response"])
        except:
            pass
        return jsonify({"success": True, "payment": rec})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500

if __name__ == "__main__":
    # don't init_db here if you are 100% sure table already exists, but safe to call
    init_db()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
