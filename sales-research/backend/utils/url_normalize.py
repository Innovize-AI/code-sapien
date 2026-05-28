import urllib.parse
from typing import Optional

def normalize_linkedin_url(url: Optional[str]) -> Optional[str]:
    """
    Normalizes a LinkedIn URL by:
    1. Stripping whitespace
    2. Removing query parameters
    3. Removing trailing slashes
    4. Ensuring https scheme and standardizing domain to linkedin.com
    """
    if not url:
        return url
    
    url = url.strip()
    
    # Handle Apollo IDs or other non-URL identifiers
    if url.startswith('apollo_id:'):
        return url
    
    try:
        # Add a scheme if none is present to help urlparse
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        parsed = urllib.parse.urlparse(url)
        
        # Lowercase domain and remove www.
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
            
        # Remove trailing slashes from path
        path = parsed.path.rstrip('/')
        
        # Reconstruct the URL without query parameters or fragments
        normalized = urllib.parse.urlunparse(('https', netloc, path, '', '', ''))
        return normalized
    except Exception:
        # Fallback if parsing fails
        return url.split('?')[0].rstrip('/')
