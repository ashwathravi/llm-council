
import asyncio
import httpx
import sys
import os

# Add project root to sys.path to import backend modules
sys.path.append(os.getcwd())

from backend.auth import create_access_token

API_URL = "http://localhost:8001/api"
DUMMY_UID = "user123"

async def verify_delete():
    # Generate a valid token
    token = create_access_token({"sub": DUMMY_UID, "name": "Test User"})
    headers = {"Authorization": f"Bearer {token}"}
    
    async with httpx.AsyncClient() as client:
        # 1. Create a dummy conversation
        print("Creating dummy conversation...")
        create_payload = {
            "framework": "standard",
            "council_models": [],
            "chairman_model": None
        }
        resp = await client.post(f"{API_URL}/conversations", json=create_payload, headers=headers)
        if resp.status_code != 200:
            print(f"Failed to create conversation: {resp.text}")
            return
        
        conv_id = resp.json()["id"]
        print(f"Created conversation: {conv_id}")

        # 2. Verify it exists
        resp = await client.get(f"{API_URL}/conversations", headers=headers)
        conversations = resp.json()
        if not any(c["id"] == conv_id for c in conversations):
             print("Error: Created conversation not found in list.")
             return
        print("Confirmed conversation exists.")

        # 3. Delete it
        print(f"Deleting conversation {conv_id}...")
        resp = await client.delete(f"{API_URL}/conversations/{conv_id}", headers=headers)
        print(f"Delete Status: {resp.status_code}")
        print(f"Delete Response: {resp.text}")

        if resp.status_code == 200:
             # 4. Verify it's gone
            resp = await client.get(f"{API_URL}/conversations", headers=headers)
            conversations = resp.json()
            if any(c["id"] == conv_id for c in conversations):
                 print("FAILURE: Conversation still exists after delete.")
            else:
                 print("SUCCESS: Conversation deleted.")
        else:
            print("FAILURE: Delete request failed.")

if __name__ == "__main__":
    asyncio.run(verify_delete())
