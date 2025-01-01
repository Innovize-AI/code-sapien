from workflow.state import AgentGraphState
from langchain_core.prompts import PromptTemplate
from prompts.prompts import EMAIL_PREPROCCESSOR_SYSTEM_PROMPT, EMAIL_DRAFTER_PROMPT, EMAIL_DRAFTER_PROMPT_TEMPLATE
from agents.llm_node import LLMNode
from langchain_core.output_parsers import StrOutputParser
from pydantic import BaseModel,Field
from workflow.state import EmailOutput

class EmailGenerator(LLMNode):
        
    def generate(self, state:AgentGraphState):
            """
            Generate answer

            Args:
                state (messages): The current state

            Returns:
                dict: The updated state with re-phrased question
            """
            print("---GENERATE---")
            messages = state["messages"]
            email_query = messages[0].content
            docs = messages[1:]

            # docs = last_message.content 
            print("question", email_query)
            print("calling generate function  ", docs)
            draft_prompt = PromptTemplate.from_template(
                EMAIL_DRAFTER_PROMPT
                )  #change this to fewshot examples
            # Chain
            rag_chain =  draft_prompt | self.get_llm(json_model=False).with_structured_output(EmailOutput)

            # Run
            response = rag_chain.invoke({"context": docs, "query": email_query})
            print("final_email_output", response)
            return {"email_output": response}
        
