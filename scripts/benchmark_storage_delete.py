import time
import uuid
import os
import json
from typing import Dict, Any, List

# Mocking the bundle for benchmarking
def create_mock_bundle(num_docs: int, chunks_per_doc: int, user_id: str):
    documents = []
    chunks = []
    for i in range(num_docs):
        doc_id = f"doc_{i}"
        documents.append({
            "id": doc_id,
            "user_id": user_id,
            "filename": f"file_{i}.pdf",
            "size_bytes": 1024,
            "created_at": "2023-01-01T00:00:00"
        })
        for j in range(chunks_per_doc):
            chunks.append({
                "id": str(uuid.uuid4()),
                "document_id": doc_id,
                "user_id": user_id,
                "content": "some content " * 10
            })
    return {"documents": documents, "chunks": chunks}

def original_file_delete_document_logic(bundle, document_id, user_id):
    documents = bundle.get("documents", [])
    chunks = bundle.get("chunks", [])
    new_documents = [doc for doc in documents if not (doc.get("id") == document_id and doc.get("user_id") == user_id)]
    if len(new_documents) == len(documents):
        raise ValueError("Unauthorized or not found")
    bundle["documents"] = new_documents
    bundle["chunks"] = [chunk for chunk in chunks if chunk.get("document_id") != document_id]
    return bundle

def optimized_file_delete_document_logic(bundle, document_id, user_id):
    documents = bundle.get("documents", [])

    found_idx = -1
    for i, doc in enumerate(documents):
        if doc.get("id") == document_id and doc.get("user_id") == user_id:
            found_idx = i
            break

    if found_idx == -1:
        raise ValueError("Unauthorized or not found")

    documents.pop(found_idx)
    # bundle["chunks"] remains the same logic as it needs to filter ALL chunks
    chunks = bundle.get("chunks", [])
    bundle["chunks"] = [chunk for chunk in chunks if chunk.get("document_id") != document_id]
    return bundle

def run_bench(name, func, bundle, doc_to_delete, user_id, iterations=1000):
    start = time.perf_counter()
    for _ in range(iterations):
        # We need to copy because the logic modifies in-place
        test_bundle = {
            "documents": list(bundle["documents"]),
            "chunks": list(bundle["chunks"])
        }
        func(test_bundle, doc_to_delete, user_id)
    end = time.perf_counter()
    avg_time = (end - start) / iterations
    print(f"{name}: {avg_time:.8f} seconds per call")
    return avg_time

def benchmark():
    num_docs = 1000
    chunks_per_doc = 10
    user_id = "user123"

    bundle = create_mock_bundle(num_docs, chunks_per_doc, user_id)

    print(f"Benchmarking with {num_docs} documents and {num_docs * chunks_per_doc} chunks total.")

    scenarios = [
        ("Near start", "doc_0"),
        ("Middle", f"doc_{num_docs // 2}"),
        ("Near end", f"doc_{num_docs - 1}")
    ]

    for label, doc_id in scenarios:
        print(f"\nScenario: {label}")
        orig_time = run_bench("  Original", original_file_delete_document_logic, bundle, doc_id, user_id)
        opt_time = run_bench("  Optimized", optimized_file_delete_document_logic, bundle, doc_id, user_id)
        improvement = (orig_time - opt_time) / orig_time * 100
        print(f"  Improvement: {improvement:.2f}%")

if __name__ == "__main__":
    benchmark()
