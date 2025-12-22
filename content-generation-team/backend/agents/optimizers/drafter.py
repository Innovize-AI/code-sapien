from agents.llm_node import LLMNode
from workflow.state import AgentGraphState
from langchain_core.messages import SystemMessage, HumanMessage
from prompts.page_perfector.prompts import DRAFTER_PROMPT_TEMPLATE
class Drafter(LLMNode):

    def invoke(self, state:AgentGraphState):

        keyword_knowledge= state['keyword_knowledge']
        brand_knowledge= state['brand_knowledge']
        target_keywords= state['target_keywords']
        page_analysis= state['page_analysis']
        design_instructions= state['design_instructions']
        scrape_webpage_content= state['scraped_website_content']

        "keyword_knowledge","brand_knowledge","target_keywords","page_analysis","design_instructions"
        model= self.get_llm(False)

        system_prompt= """Only output the new page content. Do not include words like "here's your text".
        Follow standard Markdown format rules:
        - H1 must start with #
        - H2s must start with ##
        - H3s must start with ###
        - Bullet lists must use dash -
        - Text must use proper line breaks
        - Links must use [link text](URL) format
        - Bold text must use double asterisks ** or double underscores __ (e.g., **bold text** or __bold text__)
        - Italic text must use single asterisk * or single underscore _ (e.g., *italic text* or _italic text_)

        You must also sell the content to the reader by following this introduction format:
        Opening Statement:
        Write a sentence or two that introduces the topic, answers key info, and captures the reader’s interest.
        Problem Statement:
        Identify a common problem or challenge related to the topic.
        Solution Introduction:
        Briefly explain how this content will solve the reader’s problem and get their desired situation.
        Bullet Points or List of Key Topics:
        List the main points or sections of the post in bullet points or a concise list.
        Value Proposition:
        Highlight the benefits or value the reader will gain from reading the post, possibly including any free resources or templates if used within the content.

        Exclude any chat messages such as ‘Here's the content for the article based on the provided outline and specifications:’.
"""

        human_prompt= DRAFTER_PROMPT_TEMPLATE.format(
            keyword_knowledge=keyword_knowledge,
            brand_knowledge=brand_knowledge,
            target_keywords=target_keywords,
            design_instructions=design_instructions,
            scrape_webpage_content= scrape_webpage_content,
            page_analysis= page_analysis
        )

        messages = [
            SystemMessage(content=system_prompt), 
            HumanMessage(content= human_prompt)
        ]

        response= model.invoke(messages)

        draft= response.content

        # state['first_draft']= draft

        return {"first_draft":draft}