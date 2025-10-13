from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from pi_python import PiNetwork
from db import save_payment, get_payment_by_id, update_payment_status
import os, traceback, time, requests
from stellar_sdk import Server, Keypair, TransactionBuilder, Network, Asset

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

# ⚙️ Cấu hình Horizon Testnet
HORIZON_TESTNET = "https://api.testnet.minepi.com"
server = Server(horizon_url=HORIZON_TESTNET)
APP_SECRET_KEY = os.getenv("APP_PRIVATE_KEY")  # ví testnet của app
APP_KEYPAIR = Keypair.from_secret(APP_SECRET_KEY)
APP_PUBLIC_KEY = APP_KEYPAIR.public_key


# ✅ Tạo payment mock (để frontend cũ không lỗi)
@app.route("/api/create-payment", methods=["POST"])
def create_payment():
    try:
        data = request.json
        uid = data.get("uid")
        username = data.get("username")

        if not uid and not username:
            return jsonify({"success": False, "message": "Thiếu uid hoặc username"}), 400

        identifier = uid or username
        payment_id = f"mock_{identifier}_{int(time.time())}"

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


# ✅ Approve payment
@app.route("/api/approve-payment", methods=["POST"])
def approve_payment():
    try:
        data = request.json
        payment_id = data.get("payment_id")
        if not payment_id:
            return jsonify({"error": "Thiếu payment_id"}), 400

        res = pi.approve_payment(payment_id)
        if "error" in res:
            return jsonify(res), 500

        update_payment_status(payment_id, "approved")
        return jsonify({"success": True, "payment_id": payment_id, "status": "approved"})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ✅ Complete payment
@app.route("/api/complete-payment", methods=["POST"])
def complete_payment():
    try:
        data = request.json
        payment_id = data.get("payment_id")
        txid = data.get("txid")

        if not payment_id or not txid:
            return jsonify({"error": "Thiếu payment_id hoặc txid"}), 400

        res = pi.complete_payment(payment_id, txid)
        if "error" in res:
            return jsonify(res), 500

        update_payment_status(payment_id, "completed", txid)
        return jsonify({"success": True, "payment_id": payment_id, "txid": txid, "status": "completed"})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ✅ Lấy thông tin payment
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


# ✅ API check trạng thái payment
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


# 🟣 VERIFY USER (Pi testnet)
@app.route("/api/verify-user", methods=["POST"])
def verify_user():
    try:
        data = request.get_json()
        access_token = data.get("accessToken")
        if not access_token:
            return jsonify({"error": "Thiếu accessToken"}), 400

        res = requests.get(
            "https://api.minepi.com/v2/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        if res.status_code != 200:
            return jsonify({"error": "Xác minh thất bại"}), 401

        return jsonify({"success": True, "user": res.json()})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# 🟣 A2U-DIRECT (chuyển Pi testnet)
@app.route("/api/a2u-direct", methods=["POST"])
def a2u_direct():
    try:
        data = request.get_json()
        uid = data.get("uid")
        amount = float(data.get("amount", 0))
        to_wallet = data.get("to_wallet")

        if not uid or not amount or not to_wallet:
            return jsonify({"success": False, "message": "Thiếu tham số"}), 400

        # ⚙️ Load tài khoản app testnet
        app_account = server.load_account(APP_PUBLIC_KEY)

        # ⚙️ Tạo giao dịch testnet
        tx = (
            TransactionBuilder(
                source_account=app_account,
                network_passphrase=Network.TESTNET_NETWORK_PASSPHRASE,
                base_fee=100
            )
            .append_payment_op(destination=to_wallet, amount=str(amount), asset=Asset.native())
            .set_timeout(60)
            .build()
        )

        tx.sign(APP_KEYPAIR)
        response = server.submit_transaction(tx)
        tx_hash = response["hash"]
        # ✅ Lưu log payment
        record = {
            "payment_id": tx_hash,
            "uid": uid,
            "username": data.get("username"),
            "amount": amount,
            "status": "sent",
            "to_wallet": to_wallet,
            "created_at": int(time.time())
        }
        save_payment(record)

        print(f"[A2U] ✅ {amount} Pi sent to {to_wallet}, txid={tx_hash}")

        return jsonify({
            "success": True,
            "txid": tx_hash,
            "to_wallet": to_wallet,
            "amount": amount,
            "status": "sent"
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
