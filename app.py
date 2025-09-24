from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from pi_python import PiNetwork
import os, traceback, time, requests

load_dotenv()

app = Flask(__name__)
CORS(app, origins=["https://testnet.chototpi.site"], supports_credentials=True)

# 🔐 Khởi tạo SDK Pi A2U Testnet
pi = PiNetwork()
pi.initialize(
    api_key=os.getenv("PI_API_KEY"),
    wallet_private_key=os.getenv("APP_PRIVATE_KEY"),
    env="testnet"  # luôn dùng testnet cho A2U thử nghiệm
)

@app.route("/", methods=["GET"])
def home():
    return "✅ Pi A2U Testnet backend is running."

@app.route("/api/a2u-test", methods=["POST"])
def a2u_test():
    try:
        data = request.get_json()
        uid = data.get("uid")
        amount = str(data.get("amount"))

        if not uid or not amount:
            return jsonify({"success": False, "message": "Thiếu uid hoặc amount"}), 400

        print(f"👉 ENV: {pi.env}")
        print(f"🔗 base_url: {pi.base_url}")
        print(f"🪪 APP_PUBLIC_KEY: {pi.keypair.public_key}")
        print(f"👤 Đang gửi A2U cho UID: {uid}, Amount: {amount}")

        # 🔎 B1: Kiểm tra user trên Testnet
        user_url = f"https://api.minepi.com/v2/users/{uid}"
        headers = pi.get_http_headers()
        user_res = requests.get(user_url, headers=headers)
        if user_res.status_code != 200:
            return jsonify({
                "success": False,
                "message": f"❌ Không tìm thấy user UID: {uid}"
            }), 404

        user_data = user_res.json()
        user_wallet = user_data["user"]["wallet"]["public_key"]
        print(f"🎯 User Wallet Address: {user_wallet}")

        # 🧾 B2: Tạo identifier duy nhất
        identifier = f"a2u-test-{uid[:6]}-{int(time.time())}"

        # 🪙 B3: Chuẩn bị dữ liệu payment
        payment_data = {
            "user_uid": uid,
            "amount": amount,
            "memo": identifier,
            "metadata": {"source": "a2u-test"},
            "identifier": identifier,
            "from_address": pi.keypair.public_key,
            "to_address": user_wallet,
            "network": "testnet"
        }

        # 🚀 B4: Tạo, approve, submit và complete payment trên Testnet
        payment_id = pi.create_payment(payment_data)
        pi.approve_payment(payment_id)
        txid = pi.submit_payment(payment_id, None)
        pi.complete_payment(payment_id, txid)

        print(f"✅ Đã gửi A2U Testnet thành công: {txid}")
        return jsonify({"success": True, "txid": txid, "to_wallet": user_wallet})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
