# pi_python.py
import requests
import traceback

class PiNetwork:
    def __init__(self):
        self.api_key = None
        self.wallet_private_key = None
        self.env = "testnet"  # mặc định
        self.base_url = "https://api.minepi.com/v2"

    # 🔹 Khởi tạo môi trường
    def initialize(self, api_key, wallet_private_key, env="testnet"):
        self.api_key = api_key
        self.wallet_private_key = wallet_private_key
        self.env = env.lower().strip()
        self.base_url = "https://api.minepi.com/v2"
        print(f"✅ Initialized PiNetwork in {self.env.upper()} mode")

    # 🔹 Header cho mọi API call
    def _headers(self):
        return {
            "Authorization": f"Key {self.api_key}",
            "Content-Type": "application/json"
        }

    # 🔹 Lấy thông tin thanh toán
    def get_payment(self, payment_id):
        try:
            url = f"{self.base_url}/payments/{payment_id}"
            r = requests.get(url, headers=self._headers(), timeout=15)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print("❌ Lỗi get_payment:")
            traceback.print_exc()
            return {"error": str(e)}

    # 🔹 Duyệt thanh toán
    def approve_payment(self, payment_id):
        try:
            url = f"{self.base_url}/payments/{payment_id}/approve"
            r = requests.post(url, headers=self._headers(), timeout=15)
            r.raise_for_status()
            print(f"🟢 Approved payment: {payment_id}")
            return r.json()
        except Exception as e:
            print("❌ Lỗi approve_payment:")
            traceback.print_exc()
            return {"error": str(e)}

    # 🔹 Hoàn tất thanh toán
    def complete_payment(self, payment_id, txid):
        try:
            url = f"{self.base_url}/payments/{payment_id}/complete"
            payload = {"txid": txid}
            r = requests.post(url, json=payload, headers=self._headers(), timeout=15)
            r.raise_for_status()
            print(f"✅ Completed payment {payment_id} với txid: {txid}")
            return r.json()
        except Exception as e:
            print("❌ Lỗi complete_payment:")
            traceback.print_exc()
            return {"error": str(e)}

    # 🔹 Tạo payment (dành cho Testnet hoặc Mainnet)
    def create_payment(self, payment_data):
        """
        Gửi yêu cầu tạo payment thực trên Pi Testnet/Mainnet.
        Không còn giả lập.
        """
        try:
            url = f"{self.base_url}/payments"
            r = requests.post(url, json=payment_data, headers=self._headers(), timeout=15)
            if r.status_code != 200:
                print("❌ Lỗi tạo payment:", r.text)
                return {"error": f"{r.status_code}: {r.text}"}

            data = r.json()
            print("🪙 Created payment:", data)
            return data.get("identifier") or data
            except Exception as e:
            print("❌ Lỗi create_payment:")
            traceback.print_exc()
            return {"error": str(e)}
