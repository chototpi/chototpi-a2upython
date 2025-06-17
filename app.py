from flask import Flask, request, jsonify
from pi_python import PiNetwork
from stellar_sdk import Server, TransactionBuilder, Network, Keypair, Asset
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)

PI_API_KEY = os.getenv("PI_API_KEY")
APP_PUBLIC_KEY = os.getenv("APP_PUBLIC_KEY")
APP_PRIVATE_KEY = os.getenv("APP_PRIVATE_KEY")

BASE_URL = "https://api.testnet.minepi.com"
server = Server(horizon_url=BASE_URL)
network_passphrase = "Pi Testnet"

@app.route("/", methods=["GET"])
def home():
    return "✅ Pi A2U Python backend is running."

@app.route("/api/a2u-test", methods=["POST"])
def a2u_test():
    data = request.json
    uid = data.get("uid")
    amount = data.get("amount")
    memo = "a2u-python-test"

    if not uid or not amount:
        return jsonify({ "success": False, "message": "Thiếu uid hoặc amount" }), 400

    try:
        pi = PiNetwork(PI_API_KEY)
        create_res = pi.create_payment(uid, amount, memo)
        identifier = create_res.get("identifier")
        recipient = create_res.get("recipient")

        source_account = server.load_account(APP_PUBLIC_KEY)
        base_fee = server.fetch_base_fee()
        timebounds = server.fetch_timebounds(180)

        tx = TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=base_fee,
            time_bounds=timebounds
        ).add_text_memo(memo).append_payment_op(
            destination=recipient,
            amount=str(amount),
            asset=Asset.native()
        ).build()

        keypair = Keypair.from_secret(APP_PRIVATE_KEY)
        tx.sign(keypair)
        tx_result = server.submit_transaction(tx)
        txid = tx_result["id"]

        pi.complete_payment(identifier, txid)

        return jsonify({ "success": True, "txid": txid })
    except Exception as e:
        return jsonify({ "success": False, "message": str(e) }), 500
    
if __name__ == "__main__":
    app.run(debug=True)