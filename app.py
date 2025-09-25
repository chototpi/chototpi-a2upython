from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from pi_python import PiNetwork
from db import save_payment, get_payment_by_id, update_payment_status
import os, traceback, time

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
        uid = data.get("uid")
        username = data.get("username")

        if not uid and not username:
            return jsonify({"success": False, "message": "Thiếu uid hoặc username"}), 400

        # Fake payment_id (mock)
        identifier = uid or username
        payment_id = f"mock_{identifier}_{int(time.time())}"

        # Lưu DB
        record = {
            "payment_id": payment_id,
            "uid": uid,
            "username": username,
            "amount": data.get("amount"),
            "metadata": data.get("metadata"),
            "status": "pending",
            "created_at": int(time.time())
        }
        inserted_id = save_payment(record)

        return jsonify({"success": True, "payment_id": payment_id, "db_id": inserted_id})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500


# ✅ Approve payment (chỉ admin mới gọi)
@app.route("/api/approve-payment", methods=["POST"])
def approve_payment():
    try:
        data = request.json
        payment_id = data.get("payment_id")

        if not payment_id:
            return jsonify({"error": "Thiếu payment_id"}), 400

        # Mock approve (vì testnet)
        result = {"success": True, "payment_id": payment_id, "status": "approved"}
        update_payment_status(payment_id, "approved")

        return jsonify(result)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ✅ Complete payment (người dùng submit txid)
@app.route("/api/complete-payment", methods=["POST"])
def complete_payment():
    try:
        data = request.json
        payment_id = data.get("payment_id")
        txid = data.get("txid")

        if not payment_id or not txid:
            return jsonify({"error": "Thiếu payment_id hoặc txid"}), 400

        # Mock complete (vì testnet)
        result = {"success": True, "payment_id": payment_id, "txid": txid, "status": "completed"}
        update_payment_status(payment_id, "completed", txid)

        return jsonify(result)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ✅ Xem thông tin payment (user hoặc admin)
@app.route("/api/payment/<payment_id>", methods=["GET"])
def get_payment(payment_id):
    try:
        payment = get_payment_by_id(payment_id)
        if not payment:
            return jsonify({"error": "Payment không tồn tại"}), 404

        # Convert ObjectId về string cho frontend
        payment["_id"] = str(payment["_id"])
        return jsonify(payment)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
