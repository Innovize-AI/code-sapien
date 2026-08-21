import os
import logging

logger = logging.getLogger(__name__)
import json
from typing import List

# Mock Subreddit Data (This would come from PRAW in production)
MOCK_REDDIT_POSTS = [
    {
        "id": "1",
        "subreddit": "logistics",
        "title": "Struggling with manual route planning",
        "content": "Our team spends 4 hours every morning manually re-ordering stops in Google Maps. Is there an AI tool that can just ingest our CSV and spit out an optimized route for 10 drivers?"
    },
    {
        "id": "2",
        "subreddit": "SaaS",
        "title": "Clay is getting expensive",
        "content": "I love the data enrichment but at $500/mo it's eating my margins. Searching for a lighter, cheaper alternative for just LinkedIn signal detection."
    }
]

class RedditScout:
    """Agent 1: Scrapes Reddit for relevant keywords/subreddits."""
    def get_raw_posts(self, subreddits: List[str]):
        logger.info(f"[Scout] Mining subreddits: {subreddits}...")
        return MOCK_REDDIT_POSTS

class PainAnalyzer:
    """Agent 2: Categorizes posts into specific pain points."""
    def analyze_pain(self, posts: List[dict]):
        logger.info("[Analyzer] Analyzing posts for intent and urgency...")
        analyzed = []
        for post in posts:
            # In production, this would be an LLM call
            if "manually" in post["content"].lower() or "struggling" in post["content"].lower():
                post["type"] = "Automation Pain"
            elif "expensive" in post["content"].lower():
                post["type"] = "Pricing Gap"
            analyzed.append(post)
        return analyzed

class ProductIdeator:
    """Agent 3: Generates product names and value props from pain clusters."""
    def generate_ideas(self, analyzed_posts: List[dict]):
        logger.info("[Ideator] Generating SaaS concepts from pain points...")
        ideas = []
        for post in analyzed_posts:
            if post["type"] == "Automation Pain":
                ideas.append({
                    "name": f"RouteFlow AI ({post['subreddit']})",
                    "pain": post["title"],
                    "value_prop": "Auto-optimize 10+ driver routes from CSV in 60 seconds."
                })
            elif post["type"] == "Pricing Gap":
                ideas.append({
                    "name": "SignalLite",
                    "pain": "Overpriced data enrichment",
                    "value_prop": "The affordable alternative to Clay for signal-based selling."
                })
        return ideas

def run_reddit_pipeline():
    scout = RedditScout()
    analyzer = PainAnalyzer()
    ideator = ProductIdeator()

    # 1. Scout
    raw_data = scout.get_raw_posts(["logistics", "SaaS"])
    
    # 2. Analyze
    analyzed_data = analyzer.analyze_pain(raw_data)
    
    # 3. Ideate
    saas_ideas = ideator.generate_ideas(analyzed_data)

    logger.info("\n--- NEW SAAS IDEAS FROM REDDIT ---")
    for idea in saas_ideas:
        logger.info(f"Product: {idea['name']}")
        logger.info(f"Solve: {idea['pain']}")
        logger.info(f"Angle: {idea['value_prop']}\n")

if __name__ == "__main__":
    run_reddit_pipeline()
