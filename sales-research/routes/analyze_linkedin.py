
def analyze_linkedin(linkedin_url):
    """Used to analyze a linkedin user profile and create summary of profile posts etc"""

    import requests

    profile_url = "https://linkedin-api8.p.rapidapi.com/get-profile-data-by-url"
    

    querystring = {"url":linkedin_url}

    headers = {
        "x-rapidapi-key": "9958411ebcmsh66b1d9ce41707e2p1f8b93jsncb08b597fba0",
        "x-rapidapi-host": "linkedin-api8.p.rapidapi.com"
    }

    response = requests.get(profile_url, headers=headers, params=querystring)

    profile_details= response.json()

    # print(response.json())

    posts_url = "https://linkedin-api8.p.rapidapi.com/get-profile-posts"

    querystring = {"username":profile_details["username"]}

    response = requests.get(posts_url, headers=headers, params=querystring)

    profile_posts= response.json()
    print( profile_posts.keys())    
    profile_posts= profile_posts["data"][:2] #get latest 3 posts

    print(profile_posts)
    # return profile data ans postscle
    
    merged_json = merge_json(profile_details.copy(), profile_posts)
    print(merged_json)
    return merged_json

def merge_json(json1, json2):
    for key, value in json2.items():
        if key in json1 and isinstance(json1[key], dict) and isinstance(value, dict):
            merge_json(json1[key], value)
        else:
            json1[key] = value
    return json1

if __name__== "__main__":
    analyze_linkedin("https://www.linkedin.com/in/joannastoffregen/")
