import requests
import os

class PiNetwork:
    def __init__(self, api_key):
        self.api_key = api_key

        # ⚙️ Tự chọn môi trường testnet hoặc mainnet qua biến môi trường
        base_url = os.getenv("PI_API_BASE", "https://api.minepi.com")
        self.base_url = base_url.rstrip("/")

        self.headers = {
            "Authorization": f"Key {self.api_key}",
            "Content-Type": "application/json"
        }

    def create_payment(self, user_uid, amount, memo, metadata=None):
        url = f"{self.base_url}/v2/payments"
        payload = {
            "amount": str(amount),
            "memo": memo,
            "metadata": metadata or {},
            "uid": user_uid
        }

        response = requests.post(url, json=payload, headers=self.headers)
        self._handle_error(response)
        return response.json()

    def complete_payment(self, payment_id):
        url = f"{self.base_url}/v2/payments/{payment_id}/complete"
        response = requests.post(url, headers=self.headers)
        self._handle_error(response)
        data = response.json()
        return data.get("transaction", {}).get("txid", "unknown")

    def approve_payment(self, payment_id):
        url = f"{self.base_url}/v2/payments/{payment_id}/approve"
        response = requests.post(url, headers=self.headers)
        self._handle_error(response)
        return response.json()

    def _handle_error(self, response):
        if not response.ok:
            try:
                print("❌ Pi API error:", response.status_code, response.text)
                response.raise_for_status()
            except requests.exceptions.HTTPError as e:
                e.response = response
                raise e