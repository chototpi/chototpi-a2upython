# a2u_mainnet.py
import os
import time
import traceback
from decimal import Decimal, ROUND_DOWN

from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from stellar_sdk import Keypair, Server, TransactionBuilder, Network, Asset, MuxedAccount
from pymongo import MongoClient

load_dotenv()

# --------- Config ----------
APP_PRIVATE_KEY = os.getenv("APP_PRIVATE_KEY")  # S... private key (Mainnet)
if not APP_PRIVATE_KEY:
    raise RuntimeError("Environment variable APP_PRIVATE_KEY is required")

HORIZON_URL = os.getenv("HORIZON_URL", "https://api.mainnet.minepi.com")
NETWORK_PASSPHRASE = os.getenv("NETWORK_PASSPHRASE", "Pi Mainnet")  # Pi Mainnet passphrase
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("A2U_DB", "payofpi")

# --------- Init ----------
app = Flask(__name__)
CORS(app, origins="*", supports_credentials=True)  # thay bằng domain production của bạn

server = Server(horizon_url=HORIZON_URL)
keypair = Keypair.from_secret(APP_PRIVATE_KEY)
app_public = keypair.public_key

mongo = MongoClient(MONGO_URI)
db = mongo[DB_NAME]
a2u_coll = db["a2u_transactions"]  # collection ghi log

# helper: format amount to 7 decimals (Pi uses 7 decimals in your stack)
def format_amount(amount):
    # Accept string or numeric; return string with at most 7 decimals (rounded down)
    d = Decimal(str(amount)).quantize(Decimal("0.0000001"), rounding=ROUND_DOWN)
    return format(d, 'f')

# helper: convert muxed M -> base G
def convert_muxed_to_g(address):
    # handle already G
    if not isinstance(address, str):
        raise ValueError("address must be string")
    if address.startswith("G"):
        return address
    if address.startswith("M"):
        # stellar_sdk.MuxedAccount.from_account expects a muxed string like 'M...'
        mux = MuxedAccount.from_account(address)
        # .account_id gives base G address
        return mux.account_id
    raise ValueError("Unsupported address format")

# helper: check account exists on horizon mainnet
def account_exists_on_mainnet(g_address):
    try:
        server.accounts().account_id(g_address).call()
        return True
    except Exception as e:
        # horizon raises for non-200; inspect e for 404 vs other
        # simplest: if "404" in str(e) -> not exists
        txt = str(e)
        if "404" in txt:
            return False
        # else raise to surface network error
        raise

# Endpoint: POST /api/a2u-send
# Body: { "to_address": "<G or M addr>", "amount": "0.1234567", "identifier": "optional-unique-id", "memo": "optional memo", "metadata": {...} }
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

        # prevent duplicate by identifier
        existing = a2u_coll.find_one({"identifier": identifier})
        if existing:
            return jsonify({"success": False, "message": "Duplicate identifier", "identifier": identifier}), 409

        # convert M->G if needed
        try:
            to_g = convert_muxed_to_g(to_address_raw)
        except Exception as e:
            return jsonify({"success": False, "message": f"Invalid destination address: {str(e)}"}), 400

        # check target account exists on mainnet
        try:
            exists = account_exists_on_mainnet(to_g)
        except Exception as e:
            traceback.print_exc()
            return jsonify({"success": False, "message": "Network error checking destination account"}), 502

        if not exists:
            return jsonify({"success": False, "message": "Destination account not activated on mainnet"}), 400

        # format amount
        try:
            amount_str = format_amount(amount_raw)
            # minimal validation
            Decimal(amount_str)  # may raise
        except Exception as e:
            return jsonify({"success": False, "message": f"Invalid amount: {str(e)}"}), 400

        # load source account from horizon
        try:
            source_account = server.load_account(account_id=app_public)
        except Exception as e:
            traceback.print_exc()
            return jsonify({"success": False, "message": "Unable to load source account from Horizon"}, 500)

        # (Optional) check app balance sufficient
        try:
            balances = {b["asset_type"]: b["balance"] for b in source_account.balances}
            native_balance = Decimal(balances.get("native", "0"))
            if native_balance < Decimal(amount_str):
                return jsonify({"success": False, "message": "Insufficient app balance to complete A2U"}), 400
        except Exception:
            # ignore if structure different; we will just attempt tx and rely on Horizon error
            pass

        # build transaction
        tx_builder = TransactionBuilder(
            source_account=source_account,
            network_passphrase=NETWORK_PASSPHRASE,
            base_fee=100  # you may adjust
        )

        from stellar_sdk.operations import Payment
        # use native asset (Pi)
        tx_builder.append_payment_op(destination=to_g, amount=amount_str, asset=Asset.native())

        # optional memo (string)
        if memo_text:
            from stellar_sdk import Memo
            tx_builder.add_text_memo(memo_text[:28])  # limit memo length if needed

        tx = tx_builder.build()
        tx.sign(KEYPAIR := Keypair.from_secret(APP_PRIVATE_KEY))

        # submit to horizon
        try:
            response = server.submit_transaction(tx)
            except Exception as e:
            traceback.print_exc()
            return jsonify({"success": False, "message": f"Submit failed: {str(e)}"}), 502

        # Log to mongo
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
            "status": "submitted"
        }
        a2u_coll.insert_one(record)

        return jsonify({"success": True, "tx": response, "identifier": identifier})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=False)
