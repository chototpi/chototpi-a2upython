import requests

class PiNetwork:
    def __init__(self, api_key):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Key {api_key}",
            "Content-Type": "application/json"
        }
        self.base_url = "https://api.testnet.minepi.com"

    def create_payment(self, uid, amount, memo, metadata={}):
        body = {
            "uid": uid,
            "amount": amount,
            "memo": memo,
            "metadata": metadata
        }
        response = requests.post(f"{self.base_url}/v2/payments", json=body, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def complete_payment(self, identifier, txid):
        body = { "txid": txid }
        response = requests.post(f"{self.base_url}/v2/payments/{identifier}/complete", json=body, headers=self.headers)
        response.raise_for_status()
        return response.json()
