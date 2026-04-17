
import os
import json
import time
import shutil
import tempfile
from pathlib import Path
from typing import List, Dict, Any
import sys

# Add backend to path
sys.path.append(os.getcwd())

from backend.storage import file_list_conversations
from backend import config, storage

def setup_benchmark_data(data_dir: str, num_files: int, user_id: str):
    if os.path.exists(data_dir):
        shutil.rmtree(data_dir)
    os.makedirs(data_dir, exist_ok=True)

    for i in range(num_files):
        conv_id = f"conv_{i}"
        data = {
            "id": conv_id,
            "user_id": user_id if i % 2 == 0 else "other_user",
            "created_at": f"2023-01-01T00:00:{i % 60:02d}",
            "title": f"Conversation {i}",
            "framework": "standard",
            "messages": []
        }
        with open(os.path.join(data_dir, f"{conv_id}.json"), 'w') as f:
            json.dump(data, f)

def run_benchmark(num_files: int, iterations: int):
    user_id = "test_user"

    with tempfile.TemporaryDirectory() as temp_dir:
        # Override DATA_DIR in config and storage
        original_data_dir = config.DATA_DIR
        config.DATA_DIR = temp_dir
        storage.DATA_DIR = temp_dir

        try:
            setup_benchmark_data(temp_dir, num_files, user_id)

            # Warm up
            for _ in range(5):
                 file_list_conversations(user_id)

            start_time = time.perf_counter()
            for _ in range(iterations):
                results = file_list_conversations(user_id)
            end_time = time.perf_counter()

            avg_time = (end_time - start_time) / iterations
            print(f"Benchmark with {num_files} files, {iterations} iterations:")
            print(f"Average time per call: {avg_time:.6f} seconds")
            return avg_time
        finally:
            config.DATA_DIR = original_data_dir
            storage.DATA_DIR = original_data_dir

if __name__ == "__main__":
    # Real test
    run_benchmark(100, 50)
    run_benchmark(1000, 50)
