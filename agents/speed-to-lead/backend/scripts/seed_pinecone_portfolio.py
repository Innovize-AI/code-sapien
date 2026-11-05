"""
Ingest portfolio projects into Pinecone (portfolio namespace).

Usage:
    poetry run python scripts/seed_pinecone_portfolio.py --projects-file ../docs/portfolio.json

portfolio.json format (list of project objects):
[
  {
    "id": "id-proj-001",
    "title": "Modern 3BHK — Indiranagar",
    "description": "Contemporary open-plan living with warm oak accents. Full home renovation...",
    "location": "Indiranagar, Bangalore",
    "config": "3BHK",
    "budget_bracket": "10-20L",
    "style": "contemporary",
    "image_urls": ["https://cdn.example.com/proj1/living.jpg", "..."],
    "brochure_url": "https://cdn.example.com/proj1/brochure.pdf",
    "vertical": "interior"
  },
  ...
]
"""

import argparse
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from services import claude, pinecone_svc


async def main(projects_file: str) -> None:
    if not os.path.exists(projects_file):
        print(f"File not found: {projects_file}")
        return

    with open(projects_file) as f:
        projects: list[dict] = json.load(f)

    claude.init()
    pinecone_svc.init()

    print(f"Upserting {len(projects)} portfolio projects...")
    await pinecone_svc.upsert_portfolio(projects)

    for p in projects:
        print(f"  ✓ {p['id']} — {p['title']} ({p.get('vertical', '?')})")

    print(f"\nDone. {len(projects)} projects in portfolio namespace.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--projects-file", default="../docs/portfolio.json")
    args = parser.parse_args()
    asyncio.run(main(args.projects_file))
