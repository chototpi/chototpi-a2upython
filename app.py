from flask import Flask, request, jsonify
from flask_cors import CORS
from pi_python import PiNetwork
from dotenv import load_dotenv
import os
import traceback

load_dotenv()

app = Flask(__name__)
CORS(app)

PI_API_KEY = os.getenv("PI_API_KEY")
PI_ENV = os.getenv("PI_ENV", "sandbox")

pi = PiNetwork(
    api_key=PI_API_KEY,
    env=PI_ENV
)

@app.route("/", methods=["GET"])
def home():
    return "✅ Pi A2U Python backend is running."

@app.route("/api/a2u-test", methods=["POST"])
def a2u_test():
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