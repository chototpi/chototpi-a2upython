# a2u_mainnet.py
import os
import time
import traceback
from decimal import Decimal, ROUND_DOWN

from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from pymongo import MongoClient

# ---------- Stellar SDK ----------
from stellar_sdk import (
    Keypair,
    Server,
    TransactionBuilder,
    Network,
    Asset,
    MuxedAccount,
    Memo,
    Payment,   # ✅ import Payment TRỰC TIẾP từ stellar_sdk
)

import stellar_sdk
print("✅ Stellar SDK version:", stellar_sdk.__version__)

# ---------- Config ----------
load_dotenv()
APP_PRIVATE_KEY = os.getenv("APP_PRIVATE_KEY")
if not APP_PRIVATE_KEY:
    raise RuntimeError("Environment variable APP_PRIVATE_KEY is required")

HORIZON_URL = os.getenv("HORIZON_URL", "https://api.mainnet.minepi.com")
NETWORK_PASSPHRASE = os.getenv("NETWORK_PASSPHRASE", "Pi Mainnet")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("A2U_DB", "payofpi")

# ---------- Init ----------
app = Flask(__name__)
CORS(app, origins="*", supports_credentials=True)

server = Server(horizon_url=HORIZON_URL)
keypair = Keypair.from_secret(APP_PRIVATE_KEY)
app_public = keypair.public_key

mongo = MongoClient(MONGO_URI)
db = mongo[DB_NAME]
a2u_coll = db["a2u_transactions"]

# ---------- Helpers ----------
def format_amount(amount):
    d = Decimal(str(amount)).quantize(Decimal("0.0000001"), rounding=ROUND_DOWN)
    return format(d, "f")

def convert_muxed_to_g(address: str):
    if address.startswith("G"):
        return address
    if address.startswith("M"):
        mux = MuxedAccount.from_account(address)
        return mux.account_id
    raise ValueError("Unsupported address format")

def account_exists_on_mainnet(g_address):
    try:
        server.accounts().account_id(g_address).call()
        return True
    except Exception as e:
        if "404" in str(e):
            return False
        raise

# ---------- Endpoint ----------
@app.route("/api/a2u-send", methods=["POST"])
def a2u_send():
    try:
        payload = request.get_json(force=True)
        to_address_raw = payload.get("to_address")
        amount_raw = payload.get("amount")
        identifier = payload.get("identifier") or f"a2u-{int(time.time())}"
        memo_text = payload.get("memo") or ""
        metadata = payload.get("metadata") or {}

        if not to_address_raw or not amount_raw:
            return jsonify({"success": False, "message": "Missing to_address or amount"}), 400

        if a2u_coll.find_one({"identifier": identifier}):
            return jsonify({"success": False, "message": "Duplicate identifier", "identifier": identifier}), 409

        # --- Convert M→G ---
        to_g = convert_muxed_to_g(to_address_raw)

        # --- Check account exists ---
        if not account_exists_on_mainnet(to_g):
            return jsonify({"success": False, "message": "Destination account not activated on mainnet"}), 400

        # --- Format amount ---
        amount_str = format_amount(amount_raw)
        Decimal(amount_str)  # validate numeric

        # --- Load source ---
        source_account = server.load_account(app_public)

        # --- Optional balance check ---
        try:
            balances = {b["asset_type"]: b["balance"] for b in source_account.balances}
            native_balance = Decimal(balances.get("native", "0"))
            if native_balance < Decimal(amount_str):
                return jsonify({"success": False, "message": "Insufficient app balance"}), 400
        except Exception:
            pass

        # --- Build transaction ---
        tx_builder = TransactionBuilder(
            source_account=source_account,
            network_passphrase=NETWORK_PASSPHRASE,
            base_fee=100,
        )

        tx_builder.append_payment_op(destination=to_g, amount=amount_str, asset=Asset.native())

        if memo_text:
            tx_builder.add_text_memo(memo_text[:28])

        tx = tx_builder.build()
        tx.sign(keypair)

        # --- Submit transaction ---
        try:
            response = server.submit_transaction(tx)
        except Exception as e:
            traceback.print_exc()
            return jsonify({"success": False, "message": f"Submit failed: {e}"}), 502

        # --- Log MongoDB ---
        record = {
            "identifier": identifier,
            "created_at": int(time.time()),
            "from_pub": app_public,
            "to_raw": to_address_raw,
            "to_g": to_g,
            "amount": amount_str,
            "memo": memo_text,
            "metadata": metadata,
            "horizon_result": response,
            "status": "submitted",
        }
        a2u_coll.insert_one(record)

        return jsonify({"success": True, "tx": response, "identifier": identifier})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500


# ---------- Main ----------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=False)
