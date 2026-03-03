
import time
from backend.export import export_to_markdown

def create_large_conversation(num_messages=1000, num_models=10):
    messages = []
    for i in range(num_messages):
        messages.append({
            "role": "user",
            "content": "User message " * 100
        })
        stage1 = []
        for j in range(num_models):
            stage1.append({
                "model": f"Model {j}",
                "response": "Model response " * 200
            })
        messages.append({
            "role": "assistant",
            "stage1": stage1,
            "stage2": [{"model": f"Model {j}", "ranking": "Ranking " * 50} for j in range(num_models)],
            "stage3": {"response": "Final synthesis " * 300}
        })

    return {
        "title": "Large Conversation",
        "created_at": "2025-01-01",
        "framework": "standard",
        "messages": messages
    }

def benchmark():
    conversation = create_large_conversation(num_messages=5000, num_models=10)
    print(f"Conversation size: {len(conversation['messages'])} messages")

    start_time = time.perf_counter()
    md = export_to_markdown(conversation)
    end_time = time.perf_counter()

    duration = end_time - start_time
    print(f"Time taken: {duration:.4f} seconds")
    print(f"Markdown length: {len(md)} characters")

if __name__ == "__main__":
    benchmark()
