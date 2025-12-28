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
admin_collection = db["adminlogin"]

# -------------------------------
# Admin Credentials
# -------------------------------
email = "messtrack@admin.com"
plain_password = "messtrackadmin"

hashed_password = generate_password_hash(
    plain_password,
    method="pbkdf2:sha256",
    salt_length=16
)

admin_data = {
    "_id": ObjectId("6834b88ae22ad3fba85e654b"),
    "email": email,
    "password": hashed_password
}

admin_collection.replace_one(
    {"_id": admin_data["_id"]},
    admin_data,
    upsert=True
)

print("✅ Admin inserted/updated successfully")
print("Email:", email)
print("Password:", plain_password)
