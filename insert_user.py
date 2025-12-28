from pymongo import MongoClient
from faker import Faker
from werkzeug.security import generate_password_hash
from urllib.parse import quote_plus
import random

# -------------------------------
# MongoDB Atlas Credentials
# -------------------------------
username = "nikhillanje"
password = quote_plus("ht5Awr_gYqCWJ@7")  # URL encoded
cluster = "cluster0.7coebzw.mongodb.net"
dbname = "messtrack"

uri = f"mongodb+srv://{username}:{password}@{cluster}/{dbname}?retryWrites=true&w=majority"

client = MongoClient(uri)
db = client[dbname]
users = db["users"]

# -------------------------------
# Faker (Indian Locale)
# -------------------------------
fake = Faker("en_IN")
Faker.seed(123)

# -------------------------------
# Static Data
# -------------------------------
branches = ["CSE", "IT", "ECE", "MECH", "CIVIL", "AI&DS", "AIML", "Cybersecurity", "IOT"]
years = ["1", "2", "3", "4"]
genders = ["Male", "Female"]

# -------------------------------
# Common Password (same for all)
# -------------------------------
COMMON_PASSWORD = generate_password_hash("password123")

# -------------------------------
# Helper Functions
# -------------------------------
def indian_mobile():
    return str(random.randint(6, 9)) + "".join(str(random.randint(0, 9)) for _ in range(9))

def indian_email(name):
    name_part = name.lower().replace(" ", "")
    return f"{name_part}{random.randint(10,99)}@gmail.com"

# -------------------------------
# Insert 500 Students
# -------------------------------
student_list = []

for _ in range(500):
    name = fake.name()

    student = {
        "name": name,
        "username": name.split(" ")[0].lower() + str(random.randint(1000, 9999)),
        "password": COMMON_PASSWORD,              # Same password
        "address": fake.address().replace("\n", ", "),
        "mobile_no": indian_mobile(),
        "email": indian_email(name),

        "academic_branch": random.choice(branches),
        "academic_year": random.choice(years),
        "gender": random.choice(genders),

        "status": "Approved",
        "confirmed": True,
        "user_type": "fake"                        # Tag for cleanup
    }

    student_list.append(student)

users.insert_many(student_list)

print("🎉 500 Indian Fake Students inserted successfully into MongoDB Atlas!")
