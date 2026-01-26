
from urllib.parse import urlparse
from langchain_community.document_loaders import WebBaseLoader
import requests

def add_https_if_missing(url):
    if not url:
        return url
    parsed_url = urlparse(url)
    if not parsed_url.scheme:
        return 'https://' + url
    return url

url = "www.on-nex.com"
fixed_url = add_https_if_missing(url)
print(f"Original: '{url}'")
print(f"Fixed: '{fixed_url}'")

try:
    print("Testing requests with original...")
    requests.get(url)
except Exception as e:
    print(f"Requests Error with original: {e}")

try:
    print("Testing requests with fixed...")
    # Just checking if scheme error persists, avoiding actual network call if possible or just catching it
    # But we want to see if it throws 'No scheme supplied'
    requests.get(fixed_url, timeout=1) 
except Exception as e:
    print(f"Requests Error with fixed: {e}")

try:
    print("Testing WebBaseLoader with original...")
    loader = WebBaseLoader(url)
    loader.load()
except Exception as e:
    print(f"WebBaseLoader Error with original: {e}")

try:
    print("Testing WebBaseLoader with fixed...")
    loader = WebBaseLoader(fixed_url)
    # loader.load() # This makes a request, might be slow or fail. 
    print("WebBaseLoader init successful with fixed.")
except Exception as e:
    print(f"WebBaseLoader Error with fixed: {e}")
