from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from pi_python import PiNetwork
import os, traceback, time, requests

load_dotenv()

app = Flask(__name__)
CORS(app, origins=["https://chototpi.site"], supports_credentials=True)

# 🔐 Khởi tạo SDK với APP_PRIVATE_KEY và ENV
pi = PiNetwork()
pi.initialize(
    api_key=os.getenv("PI_API_KEY"),
    wallet_private_key=os.getenv("APP_PRIVATE_KEY"),
    env=os.getenv("PI_ENV", "mainnet")  # truyền "mainnet" hoặc "testnet"
)

@app.route("/", methods=["GET"])
def home():
    return "✅ Pi A2U Python backend is running."

@app.route("/api/verify-user", methods=["POST"])
def verify_user():
    try:
        data = request.get_json()
        access_token = data.get("authResult", {}).get("accessToken")
        if not access_token:
            return jsonify({"error": "Thiếu accessToken"}), 400

        headers = {"Authorization": f"Bearer {access_token}"}
        url = f"{pi.base_url}/v2/me"
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            print("❌ Xác minh user thất bại:", response.text)
            return jsonify({"error": "User không hợp lệ"}), 401

        user_data = response.json()
        uid = user_data["user"]["uid"]
        print(f"✅ Xác minh UID: {uid}")
        print("✅ Xác minh user thành công:", user_data)
        return jsonify({"success": True, "user": user_data})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    
@app.route("/api/ping", methods=["POST", "OPTIONS"])
def ping():
    if request.method == "OPTIONS":
        # Trả về phản hồi 200 OK cho preflight
        return '', 200
    data = request.get_json()
    print("📶 Ping received:", data)
    return jsonify({"status": "ok"})

@app.route("/approve-payment", methods=["POST"])
def approve_payment():
    try:
        data = request.get_json()
        payment_id = data.get("paymentId")

        print(f"🧾 Approve paymentId: {payment_id}")
        print(f"👉 ENV: {pi.env}")
        print(f"🔗 base_url: {pi.base_url}")
        print(f"🪪 APP_PUBLIC_KEY: {pi.keypair.public_key}")

        result = pi.approve_payment(payment_id)
        return jsonify({"success": True, "approved": result})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/complete-payment", methods=["POST"])
def complete_payment():
    try:
        data = request.get_json()
        payment_id = data.get("paymentId")
        txid = data.get("txid")

        result = pi.complete_payment(payment_id, txid)
        return jsonify({"success": True, "txid": result})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/api/a2u-test", methods=["POST"])
def a2u_test():
    try:
        data = request.get_json()
        uid = data.get("uid")
        amount = str(data.get("amount"))

        print(f"👉 ENV: {pi.env}")
        print(f"🔗 base_url: {pi.base_url}")
        print(f"🪪 APP_PUBLIC_KEY: {pi.keypair.public_key}")
        print(f"👤 Đang gửi A2U cho UID: {uid}, Amount: {amount}")

        # 🔎 B1: Gọi Pi API để lấy public key người dùng
        user_url = f"{pi.base_url}/v2/users/{uid}"
        user_res = requests.get(user_url, headers=pi.get_http_headers())
        if user_res.status_code != 200:
            return jsonify({
                "success": False,
                "message": f"❌ Không tìm thấy user UID: {uid}"
            }), 404

        user_data = user_res.json()
        user_wallet = user_data["user"]["wallet"]["public_key"]

        print(f"🎯 User Wallet Address: {user_wallet}")

        # 🧾 B2: Tạo identifier duy nhất
        identifier = f"a2u-{uid[:6]}-{int(time.time())}"

        # 🪙 B3: Tạo dữ liệu giao dịch
        payment_data = {
            "user_uid": uid,
            "amount": amount,
            "memo": identifier,
            "metadata": {"source": "a2u"},
            "identifier": identifier,
            "from_address": pi.keypair.public_key,
            "to_address": user_wallet,
            "network": pi.network
        }

        # 🚀 B4: Tạo và gửi giao dịch
        payment_id = pi.create_payment(payment_data)
        txid = pi.submit_payment(payment_id, None)
        pi.complete_payment(payment_id, txid)

        print(f"✅ Đã gửi A2U thành công: {txid}")
        return jsonify({"success": True, "txid": txid, "to": user_wallet})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500