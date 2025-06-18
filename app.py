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
    wallet_private_key=os.getenv("APP_PRIVATE_KEY"),
    network=os.getenv("PI_NETWORK", "Pi Network")
)

@app.route("/api/a2u-test", methods=["POST"])
def a2u_test():
    try:
        data = request.get_json()
        uid = data.get("uid")
        amount = str(data.get("amount"))

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