from urllib.parse import urlparse

def add_https_if_missing(url):
    # Parse the URL to check its scheme
    parsed_url = urlparse(url)
    
    # If the scheme is missing, add 'https://'
    if not parsed_url.scheme:
        return 'https://' + url
    return url
