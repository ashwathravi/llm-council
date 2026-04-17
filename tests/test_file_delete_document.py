import asyncio
import os
import sys
import json
import uuid

# Add project root to sys.path to import backend modules
sys.path.append(os.getcwd())

from backend import storage

async def test_file_delete_document():
    print("Testing file_delete_document functionality...")

    # Ensure we are using file storage
    if os.getenv("DATABASE_URL"):
        print("DATABASE_URL is set. Temporarily unsetting it to test file storage.")
        db_url = os.environ.pop("DATABASE_URL")
    else:
        db_url = None

    conversation_id = str(uuid.uuid4())
    user_id = "test_user_123"

    try:
        # 1. Create a conversation
        await storage.create_conversation(conversation_id, user_id)

        # 2. Add a document (manually via storage.file_create_document)
        filename = "test_doc.pdf"
        size_bytes = 100
        doc = storage.file_create_document(conversation_id, user_id, filename, size_bytes)
        doc_id = doc["id"]
        print(f"Created document: {doc_id}")

        # Verify document exists in bundle
        bundle = storage.load_documents_bundle(conversation_id)
        assert any(d["id"] == doc_id for d in bundle["documents"]), "Document not found in bundle after creation"
        print("Document confirmed in bundle.")

        # 3. Delete the document
        storage.file_delete_document(conversation_id, doc_id, user_id)
        print(f"Deleted document: {doc_id}")

        # 4. Verify document is gone
        bundle = storage.load_documents_bundle(conversation_id)
        assert not any(d["id"] == doc_id for d in bundle["documents"]), "Document still in bundle after deletion"
        print("SUCCESS: Document removed from bundle.")

        # 5. Test unauthorized/not found
        try:
            storage.file_delete_document(conversation_id, "non_existent_id", user_id)
            print("FAILURE: Expected ValueError for non-existent document, but none was raised.")
            sys.exit(1)
        except ValueError as e:
            print(f"Correctly caught expected error: {e}")

    finally:
        # Cleanup
        if db_url:
            os.environ["DATABASE_URL"] = db_url

        # Cleanup files if they exist
        doc_path = storage.get_documents_path(conversation_id)
        if os.path.exists(doc_path):
            os.remove(doc_path)

        # Also cleanup conversation file if it exists
        conv_path = os.path.join("data", "conversations", f"{conversation_id}.json")
        if os.path.exists(conv_path):
            os.remove(conv_path)

if __name__ == "__main__":
    asyncio.run(test_file_delete_document())
