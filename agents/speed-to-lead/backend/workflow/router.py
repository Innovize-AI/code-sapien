# Merged into agents/saarthi.py. Routing is now:
#   is_fee_query() → fee.handle()
#   is_conversational() → Gemini only (no Pinecone)
#   else → Pinecone → RAG or fallback
