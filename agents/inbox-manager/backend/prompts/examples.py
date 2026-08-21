example_emails = [
    {
        "input": """Hi Pavan Kumar,

        I've been looking for someone with your expertise.

        Are you guys still hiring for the social media manager position?

        Thank you again, and please let me know if you have any other questions.

        Best,
        Greg 
        company_domain_name: innovizeai.com,
        sender_email_id: greg@innovizeai.com""",

        "output": """
            "category": "Internal",
            "needs_response": "Needs Response",
            "confidence_score": 0.95,
            "senders_domain": "innovizeai.com",
            "reason_for_category_and_needs_response": "The email is from an internal sender regarding a job position, indicating a need for a response about hiring status."
        """
    },

    {
        "input": """Hi Pavan Kumar,

        I've been looking for someone with your expertise.

        Are you guys still hiring for the social media manager position?

        Thank you again, and please let me know if you have any other questions.

        Best,
        Greg 
        company_domain_name: innovizeai.com,
        sender_email_id: greg@hubspot.com""",

        "output": """
            "category": "HR/Recruitment",
            "needs_response": "Needs Response",
            "confidence_score": 0.95,
            "senders_domain": "hubspot.com",
            "reason_for_category_and_needs_response": "The email is from a different sender regarding a job position, indicating a need for a response about hiring status."
        """
    },
    {
        "input": """Hi Pavan Kumar,

        What would be the cost to arrange a 53' dry van for a pickup on Wednesday, Dec 25, at 10:00 AM from Chicago, IL to Texas?

        Best,
        Greg 
        company_domain_name: innovizeai.com,
        sender_email_id: greg@levity.com""",

        "output": """
            "category": "Customer Support",
            "needs_response": "Needs Response",
            "confidence_score": 0.95,
            "senders_domain": "levity.com",
            "reason_for_category_and_needs_response": "The email is from a different sender requesting a quote, indicating a need for a response about shipment."
        """
    },


]

example_drafts=[]

email_intent_examples=[

    
]
