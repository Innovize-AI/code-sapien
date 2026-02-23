import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

from workflow.graph import graph
from workflow.state import AgentState

def verify_graph():
    print("Graph imported successfully.")
    # Check if node exists
    if "email_history_fetcher" in graph.nodes:
         print("Found 'email_history_fetcher' node in graph.")
    else:
         print("ERROR: 'email_history_fetcher' node NOT found in graph.")

if __name__ == "__main__":
    verify_graph()
