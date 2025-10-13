import os
import traceback
from flask import Flask, request, jsonify
from pi_python import PiNetwork

app = Flask(__name__)

# 🟣 Khởi tạo PiNetwork
pi = PiNetwork()
pi.initialize(
    api_key=os.getenv("PI_API_KEY"),               # Lấy từ biến môi trường hoặc file .env
    wallet_private_key=os.getenv("APP_PRIVATE_KEY"), # Private key ví admin
    env=os.getenv("PI_ENV", "testnet")             # testnet hoặc mainnet
)

# 🟢 ROUTER: Lấy thông tin thanh toán
@app.route("/get-payment", methods=["POST"])
def get_payment():
    try:
        data = request.get_json()
        payment_id = data.get("payment_id")
        if not payment_id:
            return jsonify({"error": "Thiếu payment_id"}), 400

        result = pi.get_payment(payment_id)
        return jsonify(result)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# 🟢 ROUTER: Duyệt thanh toán
@app.route("/approve-payment", methods=["POST"])
def approve_payment():
    try:
        data = request.get_json()
        payment_id = data.get("payment_id")
        if not payment_id:
            return jsonify({"error": "Thiếu payment_id"}), 400

        result = pi.approve_payment(payment_id)
        return jsonify(result)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# 🟢 ROUTER: Hoàn tất thanh toán (có txid)
@app.route("/complete-payment", methods=["POST"])
def complete_payment():
    try:
        data = request.get_json()
        payment_id = data.get("payment_id")
        txid = data.get("txid")

        if not payment_id or not txid:
            return jsonify({"error": "Thiếu payment_id hoặc txid"}), 400

        result = pi.complete_payment(payment_id, txid)
        return jsonify(result)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# 🟢 ROUTER: Tạo payment thực (chạy Testnet/Mainnet)
@app.route("/create-payment", methods=["POST"])
def create_payment():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Thiếu dữ liệu thanh toán"}), 400

        result = pi.create_payment(data)
        return jsonify(result)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# 🟢 Kiểm tra môi trường đang chạy
@app.route("/env", methods=["GET"])
def get_env():
    return jsonify({
        "network": pi.env,
        "base_url": pi.base_url,
        "public_key": getattr(pi, "keypair", None),
    })


# 🟢 Trang mặc định
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": f"🚀 Pi Network A2U {pi.env.upper()} server đang hoạt động!",
        "base_url": pi.base_url
    })


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
