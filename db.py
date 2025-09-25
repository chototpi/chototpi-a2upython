# db.py
import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/chototpi")
mongo_client = MongoClient(mongo_uri)
db = mongo_client.get_database()
payments_collection = db["payments"]

# ✅ Lưu payment
def save_payment(payment_data):
    try:
        result = db["payments"].insert_one(payment_data)
        return str(result.inserted_id)
    except Exception as e:
        print("❌ Mongo save_payment error:", e)
        return None

# ✅ Lấy payment theo payment_id
def get_payment_by_id(payment_id):
    try:
        return db["payments"].find_one({"payment_id": payment_id})
    except Exception as e:
        print("❌ Mongo get_payment_by_id error:", e)
        return None

# ✅ Cập nhật trạng thái payment
def update_payment_status(payment_id, status, txid=None):
    try:
        update_data = {"status": status}
        if txid:
            update_data["txid"] = txid
        db["payments"].update_one(
            {"payment_id": payment_id},
            {"$set": update_data}
        )
        return True
    except Exception as e:
        print("❌ Mongo update_payment_status error:", e)
        return False
