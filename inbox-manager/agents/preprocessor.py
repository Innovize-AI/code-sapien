import spacy
from bs4 import BeautifulSoup
import re
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from workflow.state import AgentGraphState 
from agents.node import Node
# Load spaCy model
nlp = spacy.load("en_core_web_sm")

class Preprocess(Node):

    def preprocess_email(self, state:AgentGraphState):

        if 'raw_email_body' not in state:
            raise KeyError("'raw_email_body' key is missing in the state.")
        if 'sender_email_id' not in state:
            raise KeyError("sender_email_id key is missing in the state")
        
        raw_email_body= state['raw_email_body']
        sender_email_id= state['sender_email_id']

        print("sender_email_body", sender_email_id)

        parsed_email= self.parse_email(raw_email_body)
        extracted_domain= self.extract_domain(sender_email_id)


        state['processed_email_body']= parsed_email
        state['sender_domain_name']= extracted_domain

        
        return state



    def parse_email(self, raw_email_body:str):
        # Strip HTML tags
        soup = BeautifulSoup(raw_email_body, "html.parser")
        plain_text = soup.get_text()

        # # Remove non-alphanumeric characters
        # text = re.sub(r"[^\w\s]", "", plain_text)

        # # Lowercasing
        # text = text.lower()

        # # Tokenization
        # tokens = word_tokenize(text)

        # # Remove stopwords
        # stop_words = set(stopwords.words("english"))
        # filtered_tokens = [word for word in tokens if word not in stop_words]

        # # Lemmatization
        # doc = nlp(" ".join(filtered_tokens))
        # lemmatized_tokens = [token.lemma_ for token in doc]

        return  plain_text
    

    def extract_domain(self,email_id):
        try:
            return email_id.split('@')[1]
        
        except IndexError:
            raise ValueError("Invalid email address")


