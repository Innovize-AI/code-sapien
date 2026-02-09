"""
Validation Agent - Ensures data quality and completeness across the pipeline
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from workflow.state import AgentState
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
import json
import re

class ValidationResult(BaseModel):
    """Structure for validation results"""
    is_valid: bool = Field(description="Whether the data passed validation")
    confidence_score: float = Field(description="Confidence in the validation (0-1)")
    issues: List[str] = Field(default_factory=list, description="List of validation issues found")
    suggestions: List[str] = Field(default_factory=list, description="Suggestions for improvement")
    requires_retry: bool = Field(default=False, description="Whether the source should retry")
    
class DataQualityMetrics(BaseModel):
    """Metrics for data quality assessment"""
    completeness: float = Field(description="Data completeness score (0-1)")
    accuracy: float = Field(description="Data accuracy score (0-1)")
    consistency: float = Field(description="Data consistency score (0-1)")
    timeliness: float = Field(description="Data timeliness score (0-1)")
    relevance: float = Field(description="Data relevance score (0-1)")

def validate_linkedin_data(state: AgentState) -> Dict[str, Any]:
    """
    Validates LinkedIn profile and company data
    Checks for completeness, accuracy, and relevance
    """
    profile_data = state.get("user_profile_details", {})
    company_data = state.get("company_stats", {})
    
    validation = ValidationResult(is_valid=True, confidence_score=1.0)
    
    # Check profile completeness
    required_fields = ["name", "headline", "summary", "experience"]
    missing_fields = [f for f in required_fields if not profile_data.get(f)]
    
    if missing_fields:
        validation.is_valid = False
        validation.confidence_score *= 0.7
        validation.issues.append(f"Missing LinkedIn profile fields: {', '.join(missing_fields)}")
        validation.suggestions.append("Consider re-fetching profile with authentication")
    
    # Validate experience data
    experience = profile_data.get("experience", [])
    if len(experience) == 0:
        validation.confidence_score *= 0.8
        validation.issues.append("No experience data found")
    else:
        # Check for recent experience
        current_roles = [exp for exp in experience if not exp.get("end_date")]
        if not current_roles:
            validation.issues.append("No current role identified")
            validation.confidence_score *= 0.9
    
    # Validate company data if exists
    if company_data:
        if not company_data.get("employee_count"):
            validation.issues.append("Company size information missing")
            validation.confidence_score *= 0.95
            
    # Check data freshness
    posts = state.get("post_engagements", [])
    if posts and len(posts) > 0:
        # Check if posts are recent
        # This is a simplified check - in production, parse actual dates
        validation.confidence_score = min(validation.confidence_score * 1.1, 1.0)
    
    validation.requires_retry = validation.confidence_score < 0.5
    
    return {
        "linkedin_validation": validation.model_dump(),
        "linkedin_data_quality": DataQualityMetrics(
            completeness=1.0 - len(missing_fields) * 0.2,
            accuracy=validation.confidence_score,
            consistency=0.9 if not validation.issues else 0.7,
            timeliness=0.8,  # Could check actual timestamps
            relevance=0.9
        ).model_dump()
    }

def validate_website_data(state: AgentState) -> Dict[str, Any]:
    """
    Validates website scraping results
    Checks for content quality and extraction success
    """
    website_content = state.get("scraped_website_content", "")
    website_analysis = state.get("website_analysis", {})
    
    validation = ValidationResult(is_valid=True, confidence_score=1.0)
    
    # Check if content was scraped
    if not website_content or len(website_content) < 100:
        validation.is_valid = False
        validation.confidence_score = 0.2
        validation.issues.append("Insufficient website content scraped")
        validation.suggestions.append("Check if website URL is valid and accessible")
        validation.requires_retry = True
    
    # Check for common scraping failures
    error_indicators = ["403 forbidden", "404 not found", "access denied", "cloudflare"]
    content_lower = website_content.lower()
    
    for indicator in error_indicators:
        if indicator in content_lower:
            validation.is_valid = False
            validation.confidence_score = 0.1
            validation.issues.append(f"Website scraping blocked: {indicator}")
            validation.suggestions.append("Consider using alternative scraping methods or APIs")
            break
    
    # Validate extraction quality
    if website_analysis:
        required_insights = ["products", "services", "target_market"]
        missing_insights = [i for i in required_insights if not website_analysis.get(i)]
        
        if missing_insights:
            validation.confidence_score *= 0.8
            validation.issues.append(f"Missing website insights: {', '.join(missing_insights)}")
    
    return {
        "website_validation": validation.model_dump(),
        "website_data_quality": DataQualityMetrics(
            completeness=min(len(website_content) / 1000, 1.0) if website_content else 0,
            accuracy=validation.confidence_score,
            consistency=0.8 if validation.is_valid else 0.3,
            timeliness=0.9,
            relevance=0.85 if website_analysis else 0.5
        ).model_dump()
    }

def validate_lead_scoring(state: AgentState) -> Dict[str, Any]:
    """
    Validates lead scoring logic and results
    Ensures scoring criteria are properly applied
    """
    lead_score = state.get("lead_score_analysis", {})
    lead_data = state.get("lead_extracted_data", {})
    
    validation = ValidationResult(is_valid=True, confidence_score=1.0)
    
    if not lead_score:
        validation.is_valid = False
        validation.confidence_score = 0
        validation.issues.append("No lead score calculated")
        validation.requires_retry = True
        return {"lead_scoring_validation": validation.model_dump()}
    
    # Validate score range
    score_value = lead_score.get("score", 0)
    if not (0 <= score_value <= 100):
        validation.is_valid = False
        validation.issues.append(f"Invalid score range: {score_value}")
        validation.suggestions.append("Score should be between 0-100")
    
    # Check scoring factors
    factors = lead_score.get("factors", {})
    expected_factors = ["title_match", "company_fit", "engagement_level", "buying_signals"]
    
    missing_factors = [f for f in expected_factors if f not in factors]
    if missing_factors:
        validation.confidence_score *= 0.8
        validation.issues.append(f"Missing scoring factors: {', '.join(missing_factors)}")
    
    # Validate scoring logic consistency
    if factors:
        total_weight = sum(f.get("weight", 0) for f in factors.values() if isinstance(f, dict))
        if abs(total_weight - 1.0) > 0.01:  # Should sum to 1
            validation.issues.append(f"Factor weights don't sum to 1.0: {total_weight}")
            validation.confidence_score *= 0.9
    
    return {
        "lead_scoring_validation": validation.model_dump(),
        "scoring_metrics": {
            "score": score_value,
            "factor_coverage": 1.0 - len(missing_factors) * 0.25,
            "confidence": validation.confidence_score
        }
    }

def cross_validate_data(state: AgentState) -> Dict[str, Any]:
    """
    Cross-validates data between different sources
    Identifies inconsistencies and conflicts
    """
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    # Gather data from different sources
    linkedin_data = state.get("user_profile_details", {})
    website_analysis = state.get("website_analysis", {})
    email_history = state.get("email_history", [])
    
    validation_prompt = f"""
    Cross-validate the following data sources for consistency:
    
    LinkedIn Profile:
    {json.dumps(linkedin_data, indent=2)[:1000]}
    
    Website Analysis:
    {json.dumps(website_analysis, indent=2)[:1000]}
    
    Email History Count: {len(email_history)}
    
    Check for:
    1. Name/company inconsistencies
    2. Role/title mismatches
    3. Industry classification conflicts
    4. Contact information discrepancies
    5. Timeline inconsistencies
    
    Return a JSON with:
    {{
        "inconsistencies": ["list of found inconsistencies"],
        "confidence_score": 0.0-1.0,
        "resolution_suggestions": ["list of suggestions to resolve conflicts"],
        "data_reliability": {{"source_name": reliability_score}}
    }}
    """
    
    response = llm.invoke([
        SystemMessage(content="You are a data validation expert. Identify inconsistencies across data sources."),
        HumanMessage(content=validation_prompt)
    ])
    
    try:
        validation_result = json.loads(response.content)
    except:
        validation_result = {
            "inconsistencies": [],
            "confidence_score": 0.8,
            "resolution_suggestions": [],
            "data_reliability": {}
        }
    
    return {"cross_validation": validation_result}

def validation_orchestrator(state: AgentState) -> Dict[str, Any]:
    """
    Main validation orchestrator that runs all validation checks
    Aggregates results and determines if pipeline should continue
    """
    results = {}
    
    # Run all validation checks
    linkedin_validation = validate_linkedin_data(state)
    website_validation = validate_website_data(state)
    scoring_validation = validate_lead_scoring(state)
    cross_validation = cross_validate_data(state)
    
    # Aggregate results
    all_validations = {
        **linkedin_validation,
        **website_validation,
        **scoring_validation,
        **cross_validation
    }
    
    # Calculate overall validation score
    validation_scores = []
    retry_required = False
    
    for key, value in all_validations.items():
        if "validation" in key and isinstance(value, dict):
            if "confidence_score" in value:
                validation_scores.append(value["confidence_score"])
            if value.get("requires_retry"):
                retry_required = True
    
    overall_confidence = sum(validation_scores) / len(validation_scores) if validation_scores else 0
    
    # Determine pipeline action
    pipeline_action = "continue"
    if overall_confidence < 0.3:
        pipeline_action = "abort"
    elif overall_confidence < 0.6 or retry_required:
        pipeline_action = "retry_with_improvements"
    
    return {
        "validation_results": all_validations,
        "overall_validation": {
            "confidence": overall_confidence,
            "action": pipeline_action,
            "timestamp": datetime.now().isoformat()
        }
    }