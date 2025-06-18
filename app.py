from flask import Flask, request, jsonify
from flask_cors import CORS
from pi_python import PiNetwork
from dotenv import load_dotenv
import os
import traceback

load_dotenv()

app = Flask(__name__)
CORS(app, origins=["https://chototpi.site"], supports_credentials=True)

PI_API_KEY = os.getenv("PI_API_KEY")
PI_API_BASE = os.getenv("PI_API_BASE")

pi = PiNetwork(api_key=PI_API_KEY)

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

@app.route("/api/a2u-test", methods=["POST", "OPTIONS"])
def a2u_test():
    if request.method == "OPTIONS":
        return '', 204

    data = request.get_json()
    uid = data.get("uid")
    amount = data.get("amount")

    print(f"📥 Gửi A2U cho UID: {uid}, Amount: {amount}")

    try:
        payment = pi.create_payment(
            user_uid=uid,
            amount=amount,
            memo="Test A2U",
            metadata={"debug": "true"}
        )
        txid = pi.complete_payment(payment["identifier"])
        return jsonify({"success": True, "txid": txid})
    except Exception as e:
        traceback.print_exc()
        if hasattr(e, 'response'):
            try:
                print("❌ Pi error response:", e.response.json())
                return jsonify({"success": False, "error": e.response.json()})
            except:
                pass
        return jsonify({"success": False, "message": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)