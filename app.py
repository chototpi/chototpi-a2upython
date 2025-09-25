from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from pi_python import PiNetwork
from db import save_payment, get_payment_by_id, update_payment_status
import os, traceback, time

load_dotenv()

app = Flask(__name__)
CORS(app, origins=["https://testnet.chototpi.site"], supports_credentials=True)

# 🔐 Khởi tạo SDK Pi thật trên Testnet
pi = PiNetwork()
pi.initialize(
    api_key=os.getenv("PI_API_KEY"),
    wallet_private_key=os.getenv("APP_PRIVATE_KEY"),
    env=os.getenv("PI_ENV", "testnet")  # testnet
)

# ----------------------------
# ✅ 1. Tạo payment
# ----------------------------
@app.route("/api/create-payment", methods=["POST"])
def create_payment():
    try:
        data = request.json
        uid = data.get("uid")
        username = data.get("username")
        amount = data.get("amount")
        metadata = data.get("metadata", {})

        if not uid and not username:
            return jsonify({"success": False, "message": "Thiếu uid hoặc username"}), 400

        # Thực sự gọi Pi SDK tạo payment trên Testnet
        pi_payment = pi.create_payment(
            amount=amount,
            recipient=uid,       # uid người nhận
            metadata=metadata
        )
        payment_id = pi_payment.get("id")  # ID thật từ Pi SDK

        # Lưu DB
        record = {
            "payment_id": payment_id,
            "uid": uid,
            "username": username,
            "amount": amount,
            "metadata": metadata,
            "status": "pending",
            "created_at": int(time.time())
        }
        inserted_id = save_payment(record)

        return jsonify({"success": True, "payment_id": payment_id, "db_id": inserted_id})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500

# ----------------------------
# ✅ 2. Approve payment
# ----------------------------
@app.route("/api/approve-payment", methods=["POST"])
def approve_payment():
    try:
        data = request.json
        payment_id = data.get("payment_id")

        if not payment_id:
            return jsonify({"error": "Thiếu payment_id"}), 400

        result = pi.approve_payment(payment_id)
        if "error" not in result:
            update_payment_status(payment_id, "approved")
        return jsonify(result)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ----------------------------
# ✅ 3. Complete payment
# ----------------------------
@app.route("/api/complete-payment", methods=["POST"])
def complete_payment():
    try:
        data = request.json
        payment_id = data.get("payment_id")
        txid = data.get("txid")

        if not payment_id or not txid:
            return jsonify({"error": "Thiếu payment_id hoặc txid"}), 400

        result = pi.complete_payment(payment_id, txid)
        if "error" not in result:
            update_payment_status(payment_id, "completed", txid)
        return jsonify(result)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ----------------------------
# ✅ 4. Lấy thông tin payment
# ----------------------------
@app.route("/api/payment/<payment_id>", methods=["GET"])
def get_payment(payment_id):
    try:
        payment = get_payment_by_id(payment_id)
        if not payment:
            return jsonify({"error": "Payment không tồn tại"}), 404
        payment["_id"] = str(payment["_id"])
        return jsonify(payment)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ----------------------------
# ✅ 5. Kiểm tra trạng thái payment
# ----------------------------
@app.route("/api/payment-status/<payment_id>", methods=["GET"])
def payment_status(payment_id):
    try:
        payment = get_payment_by_id(payment_id)
        if not payment:
            return jsonify({"error": "Payment không tồn tại"}), 404
        return jsonify({"payment_id": payment_id, "status": payment.get("status")})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
