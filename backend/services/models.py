from sentence_transformers import SentenceTransformer, CrossEncoder

embedding_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
rerank_model    = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")