import asyncio
import logging

logger = logging.getLogger(__name__)
import os
import csv
import sys
import json
from dotenv import load_dotenv

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from agents.linkedin_agent import batch_classify_profiles_async

async def main():
    load_dotenv()
    
    input_file = os.path.join(os.path.dirname(__file__), 'discovered_leads.csv')
    output_file = os.path.join(os.path.dirname(__file__), 'qualified_leads.csv')
    
    if not os.path.exists(input_file):
        logger.info(f"Error: {input_file} not found.")
        return

    leads = []
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        leads = list(reader)

    logger.info(f"Total leads to qualify: {len(leads)}")
    
    # Batch size for classification
    BATCH_SIZE = 15
    qualified_leads = []
    
    for i in range(0, len(leads), BATCH_SIZE):
        batch = leads[i:i+BATCH_SIZE]
        logger.info(f"Qualifying batch {i//BATCH_SIZE + 1}/{(len(leads)-1)//BATCH_SIZE + 1}...")
        
        # Prepare data for classifier
        # needs [{'id': 'url', 'headline': '...'}]
        profiles_to_classify = []
        for l in batch:
            profiles_to_classify.append({
                "id": l.get('linkedin_url'),
                "name": l.get('name'),
                "headline": l.get('headline')
            })
            
        try:
            classifications = await batch_classify_profiles_async(profiles_to_classify)
            
            for l in batch:
                url = l.get('linkedin_url')
                if url in classifications:
                    res = classifications[url]
                    l['is_fit'] = res.get('is_fit', False)
                    l['is_competitor'] = res.get('is_competitor', False)
                    l['is_decision_maker'] = res.get('is_decision_maker', False)
                    l['reasoning'] = res.get('reasoning', '')
                
                # We only keep leads that are a fit and NOT competitors
                if l.get('is_fit') and not l.get('is_competitor'):
                    qualified_leads.append(l)
                    
        except Exception as e:
            logger.info(f"Error classifying batch: {e}")

    logger.info(f"\n--- Qualification Complete ---")
    logger.info(f"Total qualified leads found: {len(qualified_leads)}")
    
    if qualified_leads:
        keys = qualified_leads[0].keys()
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            dict_writer = csv.DictWriter(f, fieldnames=keys)
            dict_writer.writeheader()
            dict_writer.writerows(qualified_leads)
        logger.info(f"Qualified leads saved to {output_file}")
    else:
        logger.info("No qualified leads found.")

if __name__ == "__main__":
    asyncio.run(main())
