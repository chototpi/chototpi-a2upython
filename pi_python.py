import requests
import json
import stellar_sdk as s_sdk

class PiNetwork:
    def __init__(self):
        self.api_key = ""
        self.keypair = None
        self.server = None
        self.account = None
        self.base_url = ""
        self.env = ""
        self.network = ""
        self.fee = 100000
        self.open_payments = {}

    def initialize(self, api_key, wallet_private_key, env="mainnet"):
        if not self.validate_private_seed_format(wallet_private_key):
            raise ValueError("❌ APP_PRIVATE_KEY không hợp lệ!")

        self.api_key = api_key
        self.env = env.lower()

        if self.env == "mainnet":
            self.base_url = "https://api.minepi.com"
            self.network = "Pi Network"
        else:
            self.base_url = "https://api.testnet.minepi.com"
            self.network = "Pi Testnet"

        self.keypair = s_sdk.Keypair.from_secret(wallet_private_key)
        horizon_url = "https://api.testnet.minepi.com" if self.env == "testnet" else "https://api.testnet.minepi.com"
        self.server = s_sdk.Server(horizon_url=horizon_url)
        self.account = self.server.load_account(self.keypair.public_key)
        self.fee = self.server.fetch_base_fee()

    def get_http_headers(self):
        return {
            "Authorization": f"Key {self.api_key}",
            "Content-Type": "application/json"
        }

    def validate_private_seed_format(self, seed):
        return seed.upper().startswith("S") and len(seed) == 56

    def create_payment(self, payment_data):
        self.open_payments[payment_data["identifier"]] = payment_data
        return payment_data["identifier"]

    def submit_payment(self, payment_id, _):
        payment = self.open_payments[payment_id]

        transaction = (
            s_sdk.TransactionBuilder(
                source_account=self.account,
                network_passphrase=self.network,
                base_fee=self.fee,
            )
            .add_text_memo(payment["memo"])
            .append_payment_op(
                destination=payment["to_address"],
                amount=str(payment["amount"]),
                asset=s_sdk.Asset.native()
            )
            .set_timeout(180)
            .build()
        )

        transaction.sign(self.keypair)
        response = self.server.submit_transaction(transaction)
        return response["id"]

    def complete_payment(self, identifier, txid=None):
        url = f"{self.base_url}/v2/payments/{identifier}/complete"
        payload = {"txid": txid} if txid else {}
        res = requests.post(url, headers=self.get_http_headers(), json=payload)
        return res.json()

    def approve_payment(self, payment_id):
        url = f"{self.base_url}/v2/payments/{payment_id}/approve"
        res = requests.post(url, headers=self.get_http_headers(), json={})
        return res.json()

    def get_user_wallet_address(self, uid):
        # 🔄 LUÔN dùng API MAINNET để lấy địa chỉ ví người dùng
        url = f"https://api.minepi.com/v2/users/{uid}"
        res = requests.get(url, headers=self.get_http_headers())
        if res.status_code != 200:
            raise ValueError(f"❌ Không tìm thấy UID: {uid}")
        data = res.json()
        return data["user"]["wallet"]["public_key"]