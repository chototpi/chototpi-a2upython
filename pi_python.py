import os
import requests
import traceback
from stellar_sdk import Keypair

class PiNetwork:
    def __init__(self):
        self.api_key = None
        self.wallet_private_key = None
        self.env = "testnet"
        self.base_url = None
        self.keypair = None
        self.network = None  # ✅ Pi Testnet / Pi Mainnet

    def initialize(self, api_key, wallet_private_key, env="testnet"):
        self.api_key = api_key
        self.wallet_private_key = wallet_private_key
        self.env = env.lower().strip()

        # ✅ Chọn URL đúng môi trường
        if self.env == "mainnet":
            self.base_url = "https://api.minepi.com/v2"
            self.network = "Pi Mainnet"
        else:
            self.base_url = "https://api.testnet.minepi.com/v2"
            self.network = "Pi Testnet"

        # ✅ Tạo keypair từ private key
        try:
            self.keypair = Keypair.from_secret(wallet_private_key)
            print(f"🔑 Wallet initialized: {self.keypair.public_key}")
        except Exception as e:
            print("⚠️ Không thể khởi tạo keypair:", e)
            self.keypair = None

    # 🔹 Header dùng cho API Pi
    def _headers(self):
        return {
            "Authorization": f"Key {self.api_key}",
            "Content-Type": "application/json"
        }

    def get_http_headers(self):
        """Dùng cho /users/{uid}"""
        return {"Authorization": f"Key {self.api_key}"}

    # 🔹 Lấy thông tin payment
    def get_payment(self, payment_id):
        try:
            url = f"{self.base_url}/payments/{payment_id}"
            r = requests.get(url, headers=self._headers(), timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            traceback.print_exc()
            return {"error": str(e)}

    # 🔹 Approve payment
    def approve_payment(self, payment_id):
        try:
            url = f"{self.base_url}/payments/{payment_id}/approve"
            r = requests.post(url, headers=self._headers(), timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            traceback.print_exc()
            return {"error": str(e)}

    # 🔹 Complete payment
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

    # 🔹 Tạo payment (chỉ hoạt động testnet/mainnet hợp lệ)
    def create_payment(self, payment_data):
        try:
            url = f"{self.base_url}/payments"
            r = requests.post(url, json=payment_data, headers=self._headers(), timeout=10)
            if r.status_code != 200:
                print("❌ Lỗi tạo payment:", r.text)
                return {"error": f"{r.status_code}: {r.text}"}

            result = r.json()
            print("🪙 Payment created:", result)
            return result.get("identifier") or result
        except Exception as e:
            traceback.print_exc()
            return {"error": str(e)}

    # 🔹 Submit payment (mock cho testnet)
    def submit_payment(self, payment_id, txid=None):
        """Hiện testnet chưa cần submit thực — chỉ trả về mã txid ảo"""
        if not payment_id or isinstance(payment_id, dict):
            fake_txid = f"TX-{int(os.urandom(2).hex(), 16)}"
        else:
            fake_txid = f"TX-{payment_id[:6]}-{int(os.urandom(2).hex(), 16)}"
        print("🚀 Submit mock txid:", fake_txid)
        return fake_txid
