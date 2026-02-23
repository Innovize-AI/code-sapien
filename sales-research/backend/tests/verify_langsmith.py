import os
from dotenv import load_dotenv

# Load environment variables from parent directories if not in current
load_dotenv(dotenv_path="../.env") # Try one level up
if not os.getenv("LANGCHAIN_API_KEY"):
    load_dotenv(dotenv_path="../../.env") # Try two levels up
load_dotenv() # Fallback to default search

def verify_langsmith_config():
    print("--- LangSmith Configuration Check ---")
    vars_to_check = [
        "LANGCHAIN_TRACING_V2",
        "LANGCHAIN_ENDPOINT",
        "LANGCHAIN_API_KEY",
        "LANGCHAIN_PROJECT"
    ]
    
    all_set = True
    for var in vars_to_check:
        value = os.getenv(var)
        if value:
            # Mask the API key for security
            if var == "LANGCHAIN_API_KEY":
                masked = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
                print(f"{var}: {masked}")
            else:
                print(f"{var}: {value}")
        else:
            print(f"{var}: NOT SET")
            all_set = False
            
    if all_set:
        print("\nSUCCESS: All LangSmith environment variables are set.")
    else:
        print("\nFAILURE: Some LangSmith environment variables are missing.")

if __name__ == "__main__":
    verify_langsmith_config()
