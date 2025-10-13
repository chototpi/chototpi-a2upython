# pi_python.py
import os
import requests
import traceback

class PiNetwork:
    def __init__(self):
        self.api_key = None
        self.wallet_private_key = None
        self.env = "testnet"  # mặc định
        self.base_url = None

    def initialize(self, api_key, wallet_private_key, env="testnet"):
        self.api_key = api_key
        self.wallet_private_key = wallet_private_key
        self.env = env
        # testnet hoặc mainnet đều gọi qua https://api.minepi.com/v2
        self.base_url = "https://api.minepi.com/v2"

    def _headers(self):
        return {
            "Authorization": f"Key {self.api_key}",
            "Content-Type": "application/json"
        }

    # ✅ Lấy thông tin payment
    def get_payment(self, payment_id):
        try:
            url = f"{self.base_url}/payments/{payment_id}"
            r = requests.get(url, headers=self._headers(), timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            traceback.print_exc()
            return {"error": str(e)}

    # ✅ Approve payment
    def approve_payment(self, payment_id):
        try:
            url = f"{self.base_url}/payments/{payment_id}/approve"
            r = requests.post(url, headers=self._headers(), timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            traceback.print_exc()
            return {"error": str(e)}

    # ✅ Complete payment (kèm txid)
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
