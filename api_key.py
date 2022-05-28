import os
import hashlib
from dotenv import load_dotenv

load_dotenv()
API_KEY_PASSWORD = os.environ["API_KEY_PASSWORD"]

# Generate api key using email and password for each user
def get_api_key(email, password=API_KEY_PASSWORD):
    return hashlib.sha256((email+password).encode()).hexdigest()

if __name__ == "__main__":
    print(get_api_key("hunkim@gmail.com"))