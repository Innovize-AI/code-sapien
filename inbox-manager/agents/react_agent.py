from agents.agent import Agent
from workflow.state import AgentGraphState
from langgraph.graph import END
from workflow.state import state
from langgraph.graph import StateGraph, MessagesState, START, END
from pydantic import BaseModel, Field
from typing import Literal
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import StrOutputParser

class ReactAgent(Agent):

    def bind_tools(self,tools):    

        self.model_with_tools = self.get_llm().bind_tools(tools)

        return self.model_with_tools
    
    def should_continue(self, state:AgentGraphState):
        messages = state["messages"]

        print("messages in should continue", messages)
        last_message = messages[-1]
        print("last_message", last_message)
        if last_message.tool_calls:
            print("call tool")
            return "tools"
        else:
            print("ended all tools called ")    
            return END


    def call_model(self, state:AgentGraphState):
        messages = state["messages"]
        response = self.model_with_tools.invoke(messages)
        return {"messages": [response]}
    

    def grade_documents(self, state:AgentGraphState) -> Literal["generator", "query_rewriter", "email_drafter"]:
        """
        Determines whether the retrieved documents are relevant to the question.

        Args:
            state (messages): The current state

        Returns:
            str: A decision for whether the documents are relevant or not
        """

        print("---CHECK RELEVANCE---")

        # Data model
        class grade(BaseModel):
            """Binary score for relevance check."""

            binary_score: str = Field(description="Relevance score 'yes' or 'no'")
            
        # LLM with tool and validation
        llm_with_tool = self.get_llm(json_model=False).with_structured_output(grade)

        # Prompt
        prompt = PromptTemplate(
            template="""You are a grader assessing relevance of a retrieved document to a user question. \n 
            Here is the retrieved document: \n\n {context} \n\n
            Here is the user question: {question} \n
            If the document contains keyword(s) or semantic meaning related to the user question, grade it as relevant. \n
            Give a binary score 'yes' or 'no' score to indicate whether the document is relevant to the question.""",
            input_variables=["context", "question"],
        )

        # Chain
        chain = prompt | llm_with_tool

        messages = state["messages"]
        last_message = messages[-1]
        
        question = messages[0].content
        docs = last_message.content
        if len(docs)==0:
            return "email_drafter"
        print("retrived document", docs)    

        scored_result = chain.invoke({"question": question, "context": docs})

        score = scored_result.binary_score

        if score == "yes":
            print("---DECISION: DOCS RELEVANT---")
            return "email_drafter"

        else:
            print("---DECISION: DOCS NOT RELEVANT---")
            print(score)
            return "query_rewriter"
        
    def query_rewriter(self, state:AgentGraphState):
        """
        Transform the query to produce a better question.

        Args:
            state (messages): The current state

        Returns:
            dict: The updated state with re-phrased question
        """

        print("---TRANSFORM QUERY---")
        messages = state["messages"]
        question = messages[0].content

        msg = [
            HumanMessage(
                content=f""" \n 
        Look at the input and try to reason about the underlying semantic intent / meaning. \n 
        Here is the initial question:
        \n ------- \n
        {question} 
        \n ------- \n
        Formulate an improved question: """,
            )
        ]

        # Grader
        response = self.get_llm(json_model=False).invoke(msg)
        return {"messages": [response]}
    

    def generate(self,state:AgentGraphState):
        """
        Generate answer

        Args:
            state (messages): The current state

        Returns:
            dict: The updated state with re-phrased question
        """
        print("---GENERATE---")
        messages = state["messages"]
        question = messages[0].content
        last_message = messages[-1]

        docs = last_message.content

        # Prompt
        prompt = """You are an assistant for question-answering tasks. Use the following pieces of retrieved context to answer the question. If you don't know the answer, just say that you don't know. Use three sentences maximum and keep the answer concise.
                    Question: {question} 
                    Context: {context} 
                    Answer:"""    

        # Chain
        rag_chain = prompt | self.get_llm(json_model=False) | StrOutputParser()

        # Run
        response = rag_chain.invoke({"context": docs, "question": question})
        return {"messages": [response]}


    
    
    
    
