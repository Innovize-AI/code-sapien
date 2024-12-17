from agents.llm_node import LLMNode
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage, AIMessage, ChatMessage
from langchain.prompts import FewShotPromptTemplate, PromptTemplate
from prompts.prompts import EMAIL_CATEGORIZER_PROMPT_TEMPLATE, email_example_template
from prompts.examples import example_emails
from workflow.state import AgentGraphState
import json

class EmailCategorizer(LLMNode):

    #prompt and create messages

    def invoke(self, state:AgentGraphState):
       
       senders_email= state['sender_email_id']
       company_domain_name= state['company_domain_name']
       email_to_analyze= state['processed_email_body']
       print("calling email categorizer", senders_email, company_domain_name)

       few_shot_prompt = FewShotPromptTemplate(
            prefix= EMAIL_CATEGORIZER_PROMPT_TEMPLATE.format(senders_email= senders_email, company_domain_name= company_domain_name),
            examples=example_emails,
            example_prompt=PromptTemplate(
                input_variables=["input", "output"],
                template=email_example_template
            ),
            suffix="Input: {new_input}\nOutput:",
            input_variables=["new_input"]
        )
    #    print( few_shot_prompt.format(new_input=email_to_analyze))
       self.messages = [
            SystemMessage(content= few_shot_prompt.format(new_input=email_to_analyze))
        ]
       
       
       print(self.messages)
       response=  self.get_llm().invoke(self.messages)

       print(response.content)
       response_json = json.loads(response.content)

       state["needs_response"]=response_json['needs_response']
       state["category"]= response_json['category']
       state["confidence_score"]= response_json['confidence_score']
       state["messages"]=  HumanMessage(content= state['processed_email_body'] )
    #    update the graph state
    #    self.update_state("needs_response", response_json['needs_response'])
    #    self.update_state("category",)
    #    self.update_state("confidence_score", response_json['confidence_score'])
    #    self.update_state("messages",) #to be passed to email drafter agent

       return state
