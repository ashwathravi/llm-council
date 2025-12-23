
try:
    from backend import main
    print("Import successful")
except SyntaxError as e:
    print(f"SyntaxError: {e}")
    exit(1)
except Exception as e:
    print(f"Other Error: {e}")
    # We might expect other errors (e.g. env vars missing), but as long as it's not SyntaxError we are good for this step
    pass
