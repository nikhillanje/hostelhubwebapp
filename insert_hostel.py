from pymongo import MongoClient
from werkzeug.security import generate_password_hash
from urllib.parse import quote_plus
from bson import ObjectId

# -------------------------------
# MongoDB Atlas Connection
# -------------------------------
username = "nikhillanje"
password = quote_plus("ht5Awr_gYqCWJ@7")
cluster = "cluster0.7coebzw.mongodb.net"
dbname = "messtrack"

uri = f"mongodb+srv://{username}:{password}@{cluster}/{dbname}?retryWrites=true&w=majority"

client = MongoClient(uri)
db = client[dbname]
xadmin_collection = db["xadminlogin"]

# -------------------------------
# X-Admin Credentials
# -------------------------------
email = "hosteladmin@hostelhub.ac.in"
plain_password = "messtrackadmin"

hashed_password = generate_password_hash(
    plain_password,
    method="pbkdf2:sha256",
    salt_length=16
)

xadmin_data = {
    "_id": ObjectId("6834b88ae22ad3fba85e654a"),
    "email": email,
    "password": hashed_password
}

xadmin_collection.replace_one(
    {"_id": xadmin_data["_id"]},
    xadmin_data,
    upsert=True
)

print("✅ X-Admin inserted/updated successfully")
print("Email:", email)
print("Password:", plain_password)
