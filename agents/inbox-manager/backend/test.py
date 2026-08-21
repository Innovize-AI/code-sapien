import spacy

nlp = spacy.load("en_core_web_sm")
# nlp.add_pipe("coreferee")

# Example text
text = "John Doe and Jane Smith are friends. John lives in New York, and Jane lives in California."
doc = nlp(text)

print(doc)
# Check coreferences
# print(doc._.coref_chains.resolve(text))