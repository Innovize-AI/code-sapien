import sys
import os

# Add the current directory to sys.path to allow imports from utils
sys.path.append(os.getcwd())

try:
    from utils import search_web_tavily, get_website_content, add_https_if_missing
    print("SUCCESS: Imports from utils.py are working.")
    
    # Test add_https_if_missing
    test_url = "google.com"
    formatted_url = add_https_if_missing(test_url)
    print(f"Test add_https_if_missing: {test_url} -> {formatted_url}")
    if formatted_url == "https://google.com":
        print("SUCCESS: add_https_if_missing works.")
    else:
        print("FAILURE: add_https_if_missing failed.")

    # Test get_website_content (mock or small live test)
    print("Testing get_website_content with https://example.com...")
    content = get_website_content("https://example.com")
    if "Example Domain" in content:
        print("SUCCESS: get_website_content works.")
    else:
        print(f"FAILURE: get_website_content returned: {content[:100]}...")

except ImportError as e:
    print(f"FAILURE: ImportError: {e}")
except Exception as e:
    print(f"FAILURE: An error occurred: {e}")
