update_payment_status(payment_id, "completed", txid)

        return jsonify(result)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ✅ Lấy thông tin payment
@app.route("/api/payment/<payment_id>", methods=["GET"])
def get_payment(payment_id):
    try:
        payment = get_payment_by_id(payment_id)
        if not payment:
            return jsonify({"error": "Payment không tồn tại"}), 404

        payment["_id"] = str(payment["_id"])
        return jsonify(payment)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ✅ API check trạng thái payment (cho frontend polling)
@app.route("/api/payment-status/<payment_id>", methods=["GET"])
def payment_status(payment_id):
    try:
        payment = get_payment_by_id(payment_id)
        if not payment:
            return jsonify({"error": "Payment không tồn tại"}), 404
        return jsonify({"payment_id": payment_id, "status": payment.get("status")})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# 🟣 1️⃣ VERIFY USER (Pi Testnet)
@app.route("/api/verify-user", methods=["POST"])
def verify_user():
    try:
        data = request.get_json()
        access_token = data.get("accessToken")

        if not access_token:
            return jsonify({"error": "Thiếu accessToken"}), 400

        res = requests.get(
            "https://api.minepi.com/v2/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        if res.status_code != 200:
            return jsonify({"error": "Xác minh thất bại"}), 401

        return jsonify({"success": True, "user": res.json()})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# 🟣 2️⃣ A2U-DIRECT (Gửi Pi Testnet)
@app.route("/api/a2u-direct", methods=["POST"])
def a2u_direct():
    try:
        data = request.get_json()
        uid = data.get("uid")
        amount = float(data.get("amount", 0))
        to_wallet = data.get("to_wallet")

        if not uid or not amount or not to_wallet:
            return jsonify({"success": False, "message": "Thiếu tham số"}), 400

        # ⚙️ Load tài khoản app testnet
        app_account = server.load_account(APP_PUBLIC_KEY)

        # ⚙️ Tạo giao dịch testnet
        tx = (
            TransactionBuilder(
                source_account=app_account,
                network_passphrase=Network.TESTNET_NETWORK_PASSPHRASE,
                base_fee=100
            )
            .append_payment_op(destination=to_wallet, amount=str(amount), asset=Asset.native())
            .set_timeout(60)
            .build()
        )

        tx.sign(APP_KEYPAIR)
        response = server.submit_transaction(tx)
        tx_hash = response["hash"]

        return jsonify({
            "success": True,
            "txid": tx_hash,
        "to_wallet": to_wallet,
            "amount": amount,
            "status": "sent"
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
