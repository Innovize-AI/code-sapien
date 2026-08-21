
def analyze_linkedin(linkedin_url):
    """Used to analyze a linkedin user profile and create summary of profile posts etc"""

    import requests
    import os
    from dotenv import load_dotenv
    load_dotenv()

    api_key = os.getenv("RAPID_API_KEY")
    linkedin_base_url = os.getenv("LINKEDIN_RAPID_BASE_URL")   


    profile_url = linkedin_base_url + "/profile/detail"
    

    querystring = {"user_name":get_username_from_url(linkedin_url)}

    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": linkedin_base_url
    }

    response = requests.get(profile_url, headers=headers, params=querystring)

    profile_details= response.json()

    # logger.info(response.json())

    posts_url = linkedin_base_url + "/profile/posts"

    querystring = {"username":profile_details["public_identifier"]}

    response = requests.get(posts_url, headers=headers, params=querystring)

    profile_posts= response.json()
    logger.info( profile_posts.keys())    
    profile_posts= profile_posts["data"][:3] #get latest 3 posts

    logger.info(profile_posts)
    # return profile data ans postscle
    
    merged_json = merge_json(profile_details.copy(), profile_posts)
    logger.info(merged_json)
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


