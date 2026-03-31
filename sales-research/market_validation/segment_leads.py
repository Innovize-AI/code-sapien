import csv
import logging

logger = logging.getLogger(__name__)
import os

def segment_leads():
    input_file = 'market_validation/qualified_leads.csv'
    output_file = 'market_validation/segmented_outreach_list.csv'
    
    if not os.path.exists(input_file):
        logger.info(f"Error: {input_file} not found.")
        return

    segmented_leads = []
    
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Logic for Angle 1: Interaction Conquest
            # If they have a competitor URL and a comment
            if row.get('competitor') and row.get('comment_text') and len(row.get('comment_text')) > 10:
                row['strategic_angle'] = 'Interaction Conquest'
                row['recommended_template'] = 'Advanced Strategy 1'
            
            # Logic for Angle 2: Persona Blueprint
            # If they are a decision maker and a good fit
            elif row.get('is_decision_maker') == 'True' and row.get('is_fit') == 'True':
                row['strategic_angle'] = 'Persona Blueprint'
                row['recommended_template'] = 'Advanced Strategy 2'
            
            # Logic for Angle 3: Thematic Intent (Keywords)
            # If they were found via keywords (competitor field is often empty or "Keyword:...")
            elif not row.get('competitor') or 'Keyword' in str(row.get('competitor')):
                row['strategic_angle'] = 'Thematic Intent'
                row['recommended_template'] = 'Advanced Strategy 3'
                
            # Fallback to Efficiency (Angle 4)
            else:
                row['strategic_angle'] = 'Agentic Efficiency'
                row['recommended_template'] = 'Advanced Strategy 4'
            
            segmented_leads.append(row)

    if segmented_leads:
        keys = segmented_leads[0].keys()
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(segmented_leads)
        
        # Summary
        stats = {}
        for l in segmented_leads:
            angle = l['strategic_angle']
            stats[angle] = stats.get(angle, 0) + 1
            
        logger.info("--- Segmentation Results ---")
        for angle, count in stats.items():
            logger.info(f"{angle}: {count} leads")
        logger.info(f"Total Segmented: {len(segmented_leads)}")
        logger.info(f"File saved to: {output_file}")

if __name__ == "__main__":
    segment_leads()
