from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from pi_python import PiNetwork
from db import save_payment, get_payment_by_id, update_payment_status
import os, traceback

load_dotenv()

app = Flask(__name__)
CORS(app, origins=["https://testnet.chototpi.site"], supports_credentials=True)

# 🔐 Khởi tạo SDK Pi
pi = PiNetwork()
pi.initialize(
    api_key=os.getenv("PI_API_KEY"),
    wallet_private_key=os.getenv("APP_PRIVATE_KEY"),
    env=os.getenv("PI_ENV", "testnet")
)

# ✅ Tạo payment
@app.route("/api/create-payment", methods=["POST"])
def create_payment():
    try:
        data = request.json
        identifier = data.get("uid") or data.get("username")
        if not identifier:
            return jsonify({"success": False, "message": "Thiếu uid hoặc username"}), 400

        # Fake payment_id (vì Pi SDK chưa hỗ trợ tạo payment trực tiếp)
        payment_id = f"mock_{identifier}_{int(time.time())}"

        # Lưu DB
        record = {
            "payment_id": payment_id,
            "amount": data.get("amount"),
            "metadata": data.get("metadata"),
            "status": "pending"
        }
        inserted_id = save_payment(record)

        return jsonify({"success": True, "payment_id": payment_id, "db_id": inserted_id})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)})

# ✅ Approve payment
@app.route("/api/approve-payment", methods=["POST"])
def approve_payment():
    try:
        data = request.json
        payment_id = data.get("payment_id")
        result = pi.approve_payment(payment_id)
        if "error" not in result:
            update_payment_status(payment_id, "approved")
        return jsonify(result)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)})

# ✅ Complete payment
@app.route("/api/complete-payment", methods=["POST"])
def complete_payment():
    try:
        data = request.json
        payment_id = data.get("payment_id")
        txid = data.get("txid")
        result = pi.complete_payment(payment_id, txid)
        if "error" not in result:
            update_payment_status(payment_id, "completed", txid)
        return jsonify(result)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
