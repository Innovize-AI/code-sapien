import sys
import os
sys.path.append('d:/innovizeai/code-sapien/sales-research/backend')
from utils.url_normalize import normalize_linkedin_url
print(normalize_linkedin_url('https://www.linkedin.com/in/test?foo=bar'))
print(normalize_linkedin_url('www.linkedin.com/in/test/'))
print(normalize_linkedin_url('linkedin.com/in/test'))
print(normalize_linkedin_url(None))
