import trend_req
# Initialize the pytrends object
pytrends = trend_req.TrendReq(hl='en-US', tz=360)

# Define your keyword or topic
topic = ["ai agents", "ai automation"]

# Build the payload
pytrends.build_payload(topic, cat=0, timeframe='today 5-y', geo='', gprop='')


# Get related queries for the topic
related_queries = pytrends.related_queries()

# Print the related queries for the specified topic
print(related_queries[topic]['top'])  # Top related queries
print(related_queries[topic]['rising'])  # Rising related queries (gaining popularity)


trending_searches = pytrends.trending_searches()
print(trending_searches.head())

related_topics = pytrends.related_topics()
print(related_topics)


# Get interest over time
interest_over_time_df = pytrends.interest_over_time()

# Display the result
print(interest_over_time_df.head())
