
import asyncio
import httpx
import jwt
import os
from datetime import datetime, timedelta

# Configuration matched to backend/auth.py
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev_secret_key_change_in_production")
ALGORITHM = "HS256"
API_URL = "http://localhost:8001/api"

def create_test_token():
    expire = datetime.utcnow() + timedelta(minutes=60)
    to_encode = {"sub": "test_user", "exp": expire}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def verify_endpoints():
    token = create_test_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    async with httpx.AsyncClient() as client:
        # 1. Test Status (No auth needed ideally, but let's check)
        print("--- Testing /api/status ---")
        try:
            resp = await client.get(f"{API_URL}/status")
            print(f"Status: {resp.status_code}")
            print(f"Response: {resp.text}")
        except Exception as e:
            print(f"Failed to fetch status: {e}")

        # 2. Test Models (Auth required)
        print("\n--- Testing /api/models ---")
        try:
            resp = await client.get(f"{API_URL}/models", headers=headers)
            print(f"Status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"Models Count: {len(data)}")
                if len(data) > 0:
                    print(f"First Model: {data[0]['id']}")
                else:
                    print("WARNING: No models returned!")
            else:
                print(f"Error Response: {resp.text}")
        except Exception as e:
            print(f"Failed to fetch models: {e}")

        # 3. Test Conversations (The reported error)
        print("\n--- Testing /api/conversations ---")
        try:
            resp = await client.get(f"{API_URL}/conversations", headers=headers)
            print(f"Status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"Conversations Count: {len(data)}")
                print("SUCCESS: Conversations list returned valid JSON")
            else:
                print(f"Error Response: {resp.text}")
        except Exception as e:
            print(f"Failed to fetch conversations: {e}")

if __name__ == "__main__":
    # Ensure backend is running!
    asyncio.run(verify_endpoints())
