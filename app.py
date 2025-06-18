from flask import Flask, request, jsonify
from flask_cors import CORS
from pi_python import PiNetwork
from stellar_sdk import Server, TransactionBuilder, Network, Keypair, Asset
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
CORS(app)

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
    data = request.get_json()
    uid = data.get("uid")
    amount = data.get("amount")

    try:
        payment = pi.create_payment(
            user_uid=uid,
            amount=amount,
            memo="Test A2U",
            metadata={"debug": "true"}  # bắt buộc có metadata
        )
        txid = pi.complete_payment(payment["identifier"])
        return jsonify({"success": True, "txid": txid})
    except Exception as e:
        if hasattr(e, 'response'):
            try:
                print("❌ Pi error response:", e.response.json())
                return jsonify({
                    "success": False,
                    "error": e.response.json()
                })
            except:
                print("❌ Raw error:", str(e))
        else:
            print("❌ General error:", str(e))

        return jsonify({"success": False, "message": str(e)})
    except Exception as e:
        import traceback
        print("❌ Lỗi xử lý A2U:")
        traceback.print_exc()  # in full stack trace vào log Render
        return jsonify({"success": False, "message": str(e)}), 500
    
if __name__ == "__main__":
    app.run(debug=True)