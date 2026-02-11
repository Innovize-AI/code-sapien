import asyncio
import os
import csv
import sys
from dotenv import load_dotenv

# Add backend to path so we can import agents
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from agents.linkedin_agent import discover_leads_from_keywords, discover_leads_from_competitor

async def main():
    load_dotenv()
    
    # Target Keywords (Problem-focused)
    keywords = [
        "sales productivity AI",
        "lead research automation",
        "personalized outreach at scale",
        "clay vs apollo",
        "SDR automation tips"
    ]
    
    # Target Competitor Profile URLs
    competitors = [
        "https://www.linkedin.com/company/clay-run/", # Clay.com
        "https://www.linkedin.com/company/apolloio/"   # Apollo.io
    ]
    
    print(f"--- Starting Lead Generation for Glial ---")
    
    all_leads = []
    
    # 1. Discover via Keywords
    print(f"\n[1/2] Searching by keywords: {keywords}")
    keyword_leads = await discover_leads_from_keywords(keywords)
    print(f"Found {len(keyword_leads)} potential leads from keyword search.")
    all_leads.extend(keyword_leads)
    
    # 2. Discover via Competitors
    print(f"\n[2/2] Searching by competitor interactions: {competitors}")
    for comp_url in competitors:
        try:
            comp_leads = discover_leads_from_competitor(comp_url)
            print(f"Found {len(comp_leads)} leads from {comp_url}")
            all_leads.extend(comp_leads)
        except Exception as e:
            print(f"Error searching competitor {comp_url}: {e}")

    # Deduplicate by LinkedIn URL
    unique_leads = {}
    for lead in all_leads:
        url = lead.get('linkedin_url')
        if url and url not in unique_leads:
            unique_leads[url] = lead
            
    final_leads = list(unique_leads.values())
    print(f"\n--- Total Unique Leads Found: {len(final_leads)} ---")
    
    # Write to CSV
    output_file = os.path.join(os.path.dirname(__file__), 'discovered_leads.csv')
    keys = final_leads[0].keys() if final_leads else []
    
    if keys:
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            dict_writer = csv.DictWriter(f, fieldnames=keys)
            dict_writer.writeheader()
            dict_writer.writerows(final_leads)
        print(f"Leads successfully exported to {output_file}")
    else:
        print("No leads to export.")

if __name__ == "__main__":
    asyncio.run(main())
