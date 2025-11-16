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

        # 1. Pi API base_url luôn dùng mainnet
        self.base_url = "https://api.minepi.com"

        # 2. Cấu hình Horizon URL cho giao dịch
        if self.env == "mainnet":
            horizon_url = "https://api.minepi.com"  # Horizon mainnet
            self.network = "Pi Network"
        else:
            horizon_url = "https://api.testnet.minepi.com"  # Horizon testnet
            self.network = "Pi Testnet"

            # 3. Load keypair + account
        self.keypair = s_sdk.Keypair.from_secret(wallet_private_key)
        self.server = s_sdk.Server(horizon_url=horizon_url)

        try:
            self.account = self.server.load_account(self.keypair.public_key)
            print(f"✅ Loaded account: {self.keypair.public_key}")
        except Exception as e:
            print(f"❌ Không thể load tài khoản: {e}")
            self.account = None

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

        # 🆕 Always refresh account to avoid tx_bad_seq
        account = self.server.load_account(self.keypair.public_key)

        transaction = (
            s_sdk.TransactionBuilder(
                source_account=account,
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

    # ---------------------------
    # 🔥 Gửi token GMOP về ví user
    # ---------------------------
    def send_token(self, asset_code, asset_issuer, amount, destination):
        print(f"🚀 Sending {amount} {asset_code} → {destination}")

        account = self.server.load_account(self.keypair.public_key)
        asset = s_sdk.Asset(asset_code, asset_issuer)

        tx = (
            s_sdk.TransactionBuilder(
                source_account=account,
                network_passphrase=self.network,
                base_fee=self.fee
            )
            .append_payment_op(
                destination=destination,
                amount=str(amount),
                asset=asset
            )
            .set_timeout(180)
            .build()
        )

        tx.sign(self.keypair)
        res = self.server.submit_transaction(tx)
        print("✅ Token transfer TX:", res)
        return res["id"]
