from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from pi_python import PiNetwork
import os, traceback, time

load_dotenv()

app = Flask(__name__)
CORS(app)

pi = PiNetwork()
pi.initialize(
    api_key=os.getenv("PI_API_KEY"),
    wallet_private_key=os.getenv("APP_PRIVATE_KEY")
)

@app.route("/", methods=["GET"])
def home():
    return "✅ Pi A2U Python backend is running."

@app.route("/approve-payment", methods=["POST"])
def approve_payment():
    try:
        data = request.get_json()
        payment_id = data.get("paymentId")
        result = pi.approve_payment(payment_id)
        print(f"✅ Approved payment: {payment_id}")
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
        result = pi.complete_payment(payment_id)
        print(f"✅ Completed payment: {payment_id}, TxID: {txid}")
        return jsonify({"success": True, "txid": result})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/api/ping", methods=["POST", "OPTIONS"])
def ping():
    if request.method == "OPTIONS":
        return '', 204
    data = request.get_json()
    print("📶 Ping received:", data)
    return jsonify({"status": "ok"})

@app.route("/api/a2u-test", methods=["POST"])
def a2u_test():
    try:
        data = request.get_json()
        uid = data.get("uid")
        amount = str(data.get("amount"))
        print(f"👉 ENV: {pi.env}")
        print(f"🔗 base_url: {pi.base_url}")
        print(f"🪪 APP_PUBLIC_KEY: {pi.keypair.public_key}")
        identifier = f"a2u-{uid[:6]}-{int(time.time())}"
        to_address = os.getenv("APP_PUBLIC_KEY")  # hoặc dynamic nếu bạn cần

        payment_data = {
            "user_uid": uid,
            "amount": amount,
            "memo": identifier,
            "metadata": {"source": "a2u"},
            "identifier": identifier,
            "from_address": pi.keypair.public_key,
            "to_address": to_address,
            "network": pi.network
        }

        payment_id = pi.create_payment(payment_data)
        txid = pi.submit_payment(payment_id, None)
        pi.complete_payment(payment_id, txid)

        return jsonify({"success": True, "txid": txid})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500