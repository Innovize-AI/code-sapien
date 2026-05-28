import logging
from typing import Optional
from models.gemini_models import get_gemini_model
from langchain_core.messages import SystemMessage, HumanMessage

logger = logging.getLogger(__name__)

STANDARD_INDUSTRIES = [
    "Accounting",
    "Aviation & Aerospace",
    "Alternative Dispute Resolution",
    "Alternative Medicine",
    "Animation",
    "Apparel & Fashion",
    "Architecture & Planning",
    "Arts & Crafts",
    "Automotive",
    "Banking",
    "Biotechnology",
    "B2B SaaS",
    "Broadcast Media",
    "Building Materials",
    "Business Supplies & Equipment",
    "Capital Markets",
    "Chemicals",
    "Civic & Social Organization",
    "Civil Engineering",
    "Commercial Real Estate",
    "Computer & Network Security",
    "Computer Games",
    "Computer Hardware",
    "Computer Networking",
    "Computer Software",
    "Construction",
    "Consumer Electronics",
    "Consumer Goods",
    "Consumer Services",
    "Cosmetics",
    "Dairy",
    "Defense & Space",
    "Design",
    "Education Management",
    "E-learning",
    "Electrical & Electronic Manufacturing",
    "Entertainment",
    "Environmental Services",
    "Events Services",
    "Executive Office",
    "Facilities Services",
    "Farming",
    "Financial Services",
    "Fine Art",
    "Fishery",
    "Food & Beverages",
    "Food Production",
    "Fundraising",
    "Furniture",
    "Gambling & Casinos",
    "Glass, Ceramics & Concrete",
    "Government Administration",
    "Government Relations",
    "Graphic Design",
    "Health, Wellness & Fitness",
    "Higher Education",
    "Hospital & Health Care",
    "Hospitality",
    "Human Resources",
    "Import & Export",
    "Individual & Family Services",
    "Industrial Automation",
    "Information Services",
    "Information Technology & Services",
    "Insurance",
    "International Affairs",
    "International Trade & Development",
    "Internet",
    "Investment Banking",
    "Investment Management",
    "Judiciary",
    "Law Enforcement",
    "Law Practice",
    "Legal Services",
    "Legislative Office",
    "Leisure, Travel & Tourism",
    "Libraries",
    "Logistics & Supply Chain",
    "Luxury Goods & Jewelry",
    "Machinery",
    "Management Consulting",
    "Maritime",
    "Marketing & Advertising",
    "Market Research",
    "Mechanical or Industrial Engineering",
    "Media Production",
    "Medical Device",
    "Medical Practice",
    "Mental Health Care",
    "Military",
    "Mining & Metals",
    "Motion Pictures & Film",
    "Museums & Institutions",
    "Music",
    "Nanotechnology",
    "Newspapers",
    "Non-profit Organization Management",
    "Oil & Energy",
    "Online Media",
    "Outsourcing/Offshoring",
    "Package/Freight Delivery",
    "Packaging & Containers",
    "Paper & Forest Products",
    "Performing Arts",
    "Pharmaceuticals",
    "Philanthropy",
    "Photography",
    "Plastics",
    "Political Organization",
    "Primary/Secondary Education",
    "Printing",
    "Professional Training & Coaching",
    "Program Development",
    "Public Policy",
    "Public Relations & Communications",
    "Public Safety",
    "Publishing",
    "Railroad Manufacture",
    "Ranching",
    "Real Estate",
    "Religious Institutions",
    "Renewables & Environment",
    "Research",
    "Restaurants",
    "Retail",
    "Security & Investigations",
    "Semiconductors",
    "Shipbuilding",
    "Sporting Goods",
    "Sports",
    "Staffing & Recruiting",
    "Supermarkets",
    "Telecommunications",
    "Textiles",
    "Think Tanks",
    "Tobacco",
    "Translation & Localization",
    "Transportation/Trucking/Railroad",
    "Utilities",
    "Venture Capital & Private Equity",
    "Veterinary",
    "Warehousing",
    "Wholesale",
    "Wine & Spirits",
    "Wireless",
    "Writing & Editing"
]

# Deterministic mapping dictionary (fast path)
KEYWORD_MAPPING = {
    "logistics": "Logistics & Supply Chain",
    "3pl": "Logistics & Supply Chain",
    "supply chain": "Logistics & Supply Chain",
    "freight": "Package/Freight Delivery",
    "cargo": "Logistics & Supply Chain",
    "trucking": "Transportation/Trucking/Railroad",
    "warehouse": "Warehousing",
    "shipping": "Logistics & Supply Chain",
    "transport": "Transportation/Trucking/Railroad",
    
    "manufactur": "Electrical & Electronic Manufacturing",
    "machinery": "Machinery",
    "automotive": "Automotive",
    "industrial": "Mechanical or Industrial Engineering",
    "aerospace": "Aviation & Aerospace",
    "aviation": "Aviation & Aerospace",
    "factory": "Mechanical or Industrial Engineering",
    "production": "Mechanical or Industrial Engineering",
    
    "construct": "Construction",
    "builder": "Construction",
    "architect": "Architecture & Planning",
    "contractor": "Construction",
    "civil engineering": "Civil Engineering",
    "real estate development": "Real Estate",
    "real estate": "Real Estate",
    
    "consult": "Management Consulting",
    "legal": "Legal Services",
    "agency": "Marketing & Advertising",
    "it services": "Information Technology & Services",
    "it & services": "Information Technology & Services",
    "outsourcing": "Outsourcing/Offshoring",
    "staffing": "Staffing & Recruiting",
    "recruitment": "Staffing & Recruiting",
    "marketing": "Marketing & Advertising",
    "advertising": "Marketing & Advertising",
    
    "finance": "Financial Services",
    "banking": "Banking",
    "account": "Accounting",
    "billing": "Financial Services",
    "fintech": "Financial Services",
    "insurance": "Insurance",
    "wealth": "Investment Management",
    "venture capital": "Venture Capital & Private Equity",
    "pe": "Venture Capital & Private Equity",
    
    "health": "Hospital & Health Care",
    "medical device": "Medical Device",
    "medical practice": "Medical Practice",
    "medical": "Hospital & Health Care",
    "hospital": "Hospital & Health Care",
    "pharma": "Pharmaceuticals",
    "clinic": "Medical Practice",
    "biotech": "Biotechnology",
    
    "b2b saas": "B2B SaaS",
    "saas": "B2B SaaS",
    "b2b": "B2B SaaS",
    "software": "Computer Software",
    "internet": "Internet",
    "telecom": "Telecommunications",
    "retail": "Retail",
    "education": "Higher Education",
    "nonprofit": "Non-profit Organization Management",
    "non-profit": "Non-profit Organization Management",
    "game": "Computer Games",
    "security": "Computer & Network Security",
    "energy": "Oil & Energy",
    "hospitality": "Hospitality"
}

def map_industry_deterministic(raw_industry: str) -> Optional[str]:
    """
    Checks if raw industry contains keywords that directly map to standard industries.
    Enforces word boundaries for short keywords to avoid false substring matches (e.g., 'pe' in 'developer').
    Returns standard industry name or None.
    """
    if not raw_industry:
        return None
    
    raw_lower = raw_industry.lower()
    import re
    
    # Check keyword matches
    for keyword, target in KEYWORD_MAPPING.items():
        if len(keyword) <= 3:
            # Match word boundary for short keywords
            if re.search(r'\b' + re.escape(keyword) + r'\b', raw_lower):
                return target
        else:
            if keyword in raw_lower:
                return target
            
    return None

async def normalize_industry(raw_industry: str) -> str:
    """
    Normalizes any raw industry string into one of our standard industries.
    Falls back to semantic analysis using Gemini if no direct keyword match exists.
    """
    if not raw_industry:
        return "Other"
    
    # 1. Deterministic Fast-Path
    matched = map_industry_deterministic(raw_industry)
    if matched:
        logger.debug(f"Deterministic industry mapping: '{raw_industry}' -> '{matched}'")
        return matched
    
    # 2. Semantic Slow-Path Fallback
    try:
        model = get_gemini_model(model="gemini-3-flash-preview", temperature=0)
        prompt = f"""
        Map the following raw company industry string to the single most relevant target industry from the standard options list.
        If it does not fit any of the standard options, return 'Other'.
        
        Raw Industry: "{raw_industry}"
        
        Standard Options:
        {STANDARD_INDUSTRIES}
        
        Return ONLY the exact option name or 'Other'. Do not include any punctuation, quotes, explanation, or markdown formatting.
        """
        messages = [
            SystemMessage(content="You are an industry normalization helper. You map complex industry names to standard sectors."),
            HumanMessage(content=prompt)
        ]
        response = await model.ainvoke(messages)
        content = response.content
        if isinstance(content, list):
            text_parts = []
            for part in content:
                if isinstance(part, str):
                    text_parts.append(part)
                elif isinstance(part, dict):
                    text_parts.append(part.get("text", ""))
                else:
                    text_parts.append(str(part))
            content_str = "".join(text_parts)
        elif isinstance(content, str):
            content_str = content
        else:
            content_str = str(content)
            
        mapped = content_str.strip().replace('"', '').replace("'", "")
        
        if mapped in STANDARD_INDUSTRIES:
            logger.info(f"Semantic industry mapping: '{raw_industry}' -> '{mapped}'")
            return mapped
        
        logger.info(f"Semantic industry mapping fell back to 'Other' for: '{raw_industry}'")
        return "Other"
    except Exception as e:
        logger.error(f"Error in normalize_industry semantic map: {e}")
        return "Other"
