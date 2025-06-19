import requests
import json
import stellar_sdk as s_sdk
import os

class PiNetwork:
    api_key = ""
    keypair = ""
    server = ""
    account = ""
    fee = ""
    base_url = ""
    open_payments = {}
    env = ""
    network = ""

    def initialize(self, api_key, wallet_private_key, network="mainnet"):
        if not self.validate_private_seed_format(wallet_private_key):
            raise ValueError("❌ APP_PRIVATE_KEY không hợp lệ!")

        self.api_key = api_key

        if network.lower() == "mainnet":
            self.base_url = "https://api.minepi.com"
            self.network = "Pi Network"
        else:
            self.base_url = "https://api.testnet.minepi.com"
            self.network = "Pi Testnet"

        self.load_account(wallet_private_key, self.network)
        self.open_payments = {}
        self.fee = self.server.fetch_base_fee()

    def load_account(self, private_seed, network):
        self.keypair = s_sdk.Keypair.from_secret(private_seed)

        if network.lower() == "mainnet" or network == "Pi Network":
            horizon = "https://api.mainnet.minepi.com"
        else:
            horizon = "https://api.testnet.minepi.com"

        self.server = s_sdk.Server(horizon)
        self.account = self.server.load_account(self.keypair.public_key)

    def validate_private_seed_format(self, seed):
        return seed.upper().startswith("S") and len(seed) == 56

    def validate_payment_data(self, data):
        required = ["amount", "memo", "metadata", "user_uid", "identifier", "to_address"]
        return all(k in data for k in required)

    def get_http_headers(self):
        return {
            "Authorization": "Key " + self.api_key,
            "Content-Type": "application/json"
        }

    def handle_http_response(self, response):
        try:
            result = response.json()
            if __debug__:
                print("📡 Pi API response:", result)
            return result
        except:
            print("❌ Không thể parse JSON từ response:", response.text)
            return False

    def create_payment(self, payment_data):
        if not self.validate_payment_data(payment_data):
            print("❌ payment_data không hợp lệ.")
            return ""

        balances = self.server.accounts().account_id(self.keypair.public_key).call()["balances"]
        for bal in balances:
            if bal["asset_type"] == "native":
                if float(payment_data["amount"]) + (float(self.fee) / 10**7) > float(bal["balance"]):
                    print("❌ Không đủ Pi để gửi.")
                    return ""

        obj = json.dumps({ "payment": payment_data })
        url = f"{self.base_url}/v2/payments"
        res = requests.post(url, data=obj, json=json.loads(obj), headers=self.get_http_headers())
        parsed = self.handle_http_response(res)

        if 'error' in parsed and 'payment' in parsed:
            identifier = parsed['payment']['identifier']
            self.open_payments[identifier] = parsed['payment']
            return identifier
        elif 'identifier' in parsed:
            identifier = parsed['identifier']
            self.open_payments[identifier] = parsed
            return identifier
        else:
            return ""

    def build_a2u_transaction(self, payment):
        if not self.validate_payment_data(payment):
            print("❌ Dữ liệu giao dịch không hợp lệ.")
            return None

        amount = str(payment["amount"])
        to_address = payment["to_address"]
        memo = payment["identifier"]

        tx = (
            s_sdk.TransactionBuilder(
                source_account=self.account,
                network_passphrase=self.network,
                base_fee=self.fee
            )
            .add_text_memo(memo)
            .append_payment_op(to_address, s_sdk.Asset.native(), amount)
            .set_timeout(180)
            .build()
        )
        return tx

    def submit_transaction(self, transaction):
        transaction.sign(self.keypair)
        response = self.server.submit_transaction(transaction)
        return response["id"]

    def submit_payment(self, payment_id, pending_payment=None):
        if payment_id not in self.open_payments and not pending_payment:
            return ""
        payment = self.open_payments.get(payment_id) or pending_payment

        balances = self.server.accounts().account_id(self.keypair.public_key).call()["balances"]
        for b in balances:
            if b["asset_type"] == "native":
                if float(payment["amount"]) + (float(self.fee) / 10**7) > float(b["balance"]):
                    return ""
                break

        tx = self.build_a2u_transaction(payment)
        txid = self.submit_transaction(tx)

        if payment_id in self.open_payments:
            del self.open_payments[payment_id]

        return txid
    
    def approve_payment(self, payment_id):
        url = f"{self.base_url}/v2/payments/{payment_id}/approve"
        res = requests.post(url, headers=self.get_http_headers())
        return self.handle_http_response(res)

    def complete_payment(self, payment_id, txid):
        obj = json.dumps({"txid": txid})
        url = f"{self.base_url}/v2/payments/{payment_id}/complete"
        res = requests.post(url, data=obj, json=json.loads(obj), headers=self.get_http_headers())
        return self.handle_http_response(res)
    
    def get_http_headers(self):
        return {
            "Authorization": "Key " + self.api_key,
            "Content-Type": "application/json"
        }

    def get_user_wallet_address(self, uid):
        url = f"{self.base_url}/v2/users/{uid}"
        res = requests.get(url, headers=self.get_http_headers())
        if res.status_code != 200:
            raise ValueError(f"❌ Không tìm thấy UID: {uid}")
        data = res.json()
        return data["user"]["wallet"]["public_key"]