from pymongo import MongoClient
from urllib.parse import quote_plus

# MongoDB Atlas
username = "nikhillanje"
password = quote_plus("ht5Awr_gYqCWJ@7")
cluster = "cluster0.7coebzw.mongodb.net"
dbname = "messtrack"

uri = f"mongodb+srv://{username}:{password}@{cluster}/{dbname}?retryWrites=true&w=majority"

client = MongoClient(uri)
db = client[dbname]
users = db["users"]

result = users.delete_many({"user_type": "fake"})

print(f"🗑 Deleted {result.deleted_count} fake users from cloud")
