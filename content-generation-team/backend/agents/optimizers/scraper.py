#scrape webpages node
from agents.node import Node
from workflow.state import AgentGraphState

from langchain_community.document_loaders import WebBaseLoader

class WebsiteScraper(Node):

    def scrape_webpages(self, state:AgentGraphState):
        """Use requests and bs4 to scrape the provided web pages for detailed information."""
        print("website " , state["url_to_scrape"])

        url= state["url_to_scrape"]
        # we could not find website
        if len(url)==0:
            return {"scraped_website_content", "Could not scrape empty website"}


        loader = WebBaseLoader(url)

        docs = loader.load()
        print("docs", docs)
        scraped_website_content= "\n\n".join(
            [
                f'{doc.page_content}'
                for doc in docs
            ]
        )
        # state['scraped_website_content']= scraped_website_content

        return {"scraped_website_content":scraped_website_content}