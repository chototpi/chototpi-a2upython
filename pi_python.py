import os
import requests
import traceback
from stellar_sdk import Keypair, Server, TransactionBuilder, Network


class PiNetwork:
    def __init__(self):
        self.api_key = None
        self.wallet_private_key = None
        self.env = "testnet"
        self.base_url = "https://api.minepi.com/v2"
        self.keypair = None
        self.network = None  # Pi Mainnet / Pi Testnet

    # ✅ Khởi tạo môi trường
    def initialize(self, api_key, wallet_private_key, env="testnet"):
        self.api_key = api_key
        self.wallet_private_key = wallet_private_key
        self.env = env.lower().strip()

        # ✅ Dùng chung API endpoint, chỉ đổi network name
        self.base_url = "https://api.minepi.com/v2"
        self.network = "Pi Mainnet" if self.env == "mainnet" else "Pi Testnet"

        # ✅ Khởi tạo keypair
        try:
            self.keypair = Keypair.from_secret(wallet_private_key)
            print(f"🔑 Wallet initialized: {self.keypair.public_key}")
        except Exception as e:
            print("⚠️ Không thể khởi tạo keypair:", e)
            self.keypair = None

    # =============================
    # 🔹 HEADER DÙNG CHO PI API
    # =============================
    def _headers(self):
        return {
            "Authorization": f"Key {self.api_key}",
            "Content-Type": "application/json"
        }

    def get_http_headers(self):
        """Dùng cho /users/{uid}"""
        return {"Authorization": f"Key {self.api_key}"}

    # =============================
    # 🔹 LẤY THÔNG TIN PAYMENT
    # =============================
    def get_payment(self, payment_id):
        try:
            url = f"{self.base_url}/payments/{payment_id}"
            r = requests.get(url, headers=self._headers(), timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            traceback.print_exc()
            return {"error": str(e)}

    # =============================
    # 🔹 APPROVE PAYMENT
    # =============================
    def approve_payment(self, payment_id):
        try:
            url = f"{self.base_url}/payments/{payment_id}/approve"
            r = requests.post(url, headers=self._headers(), timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            traceback.print_exc()
            return {"error": str(e)}

    # =============================
    # 🔹 COMPLETE PAYMENT
    # =============================
    def complete_payment(self, payment_id, txid):
        try:
            url = f"{self.base_url}/payments/{payment_id}/complete"
            payload = {"txid": txid}
            r = requests.post(url, json=payload, headers=self._headers(), timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            traceback.print_exc()
            return {"error": str(e)}

    # =============================
    # 🔹 TẠO PAYMENT
    # =============================
    def create_payment(self, payment_data):
        try:
            url = f"{self.base_url}/payments"
            r = requests.post(url, json=payment_data, headers=self._headers(), timeout=10)
            if r.status_code not in (200, 201):
                print("❌ Lỗi tạo payment:", r.text)
                return {"error": f"{r.status_code}: {r.text}"}

            result = r.json()
            print("🪙 Payment created:", result)
            return result.get("identifier") or result
        except Exception as e:
            traceback.print_exc()
            return {"error": str(e)}

    # =============================
    # 🔹 GỬI GIAO DỊCH THỰC TRÊN TESTNET
    # =============================
    def submit_payment(self, payment_id, txid=None):
        try:
            # ✅ Lấy thông tin payment từ Pi API
            payment = self.get_payment(payment_id)
            if not payment or "error" in payment:
                raise Exception("Không lấy được thông tin payment.")

            to_wallet = payment.get("to_address")
            amount = str(payment.get("amount"))

            if not to_wallet or not to_wallet.startswith("G"):
                raise Exception("Địa chỉ ví đích không hợp lệ.")

            # ✅ Kết nối Horizon Testnet
            server = Server("https://api.testnet.minepi.com")

            # ✅ Load tài khoản nguồn
            source_keypair = Keypair.from_secret(self.wallet_private_key)
            source_account = server.load_account(source_keypair.public_key)

            # ✅ Xây giao dịch chuyển Pi
            tx = (
                TransactionBuilder(
                    source_account=source_account,
                    network_passphrase=Network.TESTNET_NETWORK_PASSPHRASE,
                    base_fee=100
                )
                .append_payment_op(destination=to_wallet, amount=amount, asset_code="PI")
                .set_timeout(30)
                .build()
            )

            # ✅ Ký và gửi
            tx.sign(source_keypair)
            response = server.submit_transaction(tx)

            tx_hash = response["hash"]
            print(f"✅ Transaction success! Hash: {tx_hash}")

            return tx_hash

        except Exception as e:
            traceback.print_exc()
            return {"error": str(e)}
