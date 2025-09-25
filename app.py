from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os, traceback, time, requests, json
import mysql.connector
from pi_python import PiNetwork

# Load biến môi trường từ .env
load_dotenv()

# ⚡ Kết nối DB MySQL
def get_db_connection():
    conn = None
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "pi_payments"),
            port=int(os.getenv("DB_PORT", 3306))
        )
    except Exception as e:
        print("❌ DB connection error:", e)
    return conn

# ⚡ Flask app
app = Flask(__name__)
CORS(app, origins=["https://testnet.chototpi.site"], supports_credentials=True)

# ⚡ Khởi tạo SDK Pi A2U
pi = PiNetwork()
pi.initialize(
    api_key=os.getenv("PI_API_KEY"),
    wallet_private_key=os.getenv("APP_PRIVATE_KEY"),
    env=os.getenv("PI_ENV", "testnet")
)

# ========== API DEMO ==========

@app.route("/")
def index():
    return jsonify({"message": "✅ Pi Backend is running!"})

# API tạo payment (demo)
@app.route("/api/create-payment", methods=["POST"])
def create_payment():
    try:
        data = request.json
        payment_id = pi.create_payment(data)

        # Lưu DB
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO payments (payment_id, identifier, uid, amount, status, created_at, updated_at, raw_response)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE updated_at = VALUES(updated_at)
            """, (
                payment_id,
                data.get("identifier"),
                data.get("uid"),
                data.get("amount"),
                "pending",
                int(time.time()),
                int(time.time()),
                json.dumps(data)
            ))
            conn.commit()
            conn.close()

        return jsonify({"success": True, "payment_id": payment_id})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

# API approve payment
@app.route("/api/approve-payment", methods=["POST"])
def approve_payment():
    try:
        data = request.json
        payment_id = data.get("payment_id")
        result = pi.approve_payment(payment_id)
        return jsonify(result)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# API complete payment
@app.route("/api/complete-payment", methods=["POST"])
def complete_payment():
    try:
        data = request.json
        payment_id = data.get("payment_id")
        txid = data.get("txid")
        result = pi.complete_payment(payment_id, txid)

        # Update DB
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE payments SET status=%s, txid=%s, updated_at=%s
                WHERE payment_id=%s
            """, (
                "completed",
                txid,
                int(time.time()),
                payment_id
            ))
            conn.commit()
            conn.close()

        return jsonify(result)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ========== MAIN ==========
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
