from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
from langchain_community.tools.tavily_search import TavilySearchResults

def add_https_if_missing(url):
    # Parse the URL to check its scheme
    parsed_url = urlparse(url)
    
    # If the scheme is missing, add 'https://'
    if not parsed_url.scheme:
        return 'https://' + url
    return url

def search_web_tavily(query: str):
    """
    Search the web using Tavily.
    """
    tavily_tool = TavilySearchResults(max_results=5)
    try:
        results = tavily_tool.invoke({"query": query})
        return results
    except Exception as e:
        print(f"Error during Tavily search: {e}")
        return []

def get_website_content(url: str):
    """
    Fetch and parse website content.
    """
    url = add_https_if_missing(url)
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script and style elements
        for script_or_style in soup(["script", "style"]):
            script_or_style.decompose()
            
        # Get text
        text = soup.get_text()
        
        # Break into lines and remove leading and trailing whitespace
        lines = (line.strip() for line in text.splitlines())
        # Break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        # Drop blank lines
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text
    except Exception as e:
        print(f"Error fetching website content: {e}")
        return f"Error: Could not fetch content from {url}"
