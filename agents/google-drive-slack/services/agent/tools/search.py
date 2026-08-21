from langchain_community.tools.tavily_search import TavilySearchResults

def get_search_tool():
    search = TavilySearchResults()

    return search