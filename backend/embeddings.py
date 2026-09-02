from sentence_transformers import SentenceTransformer

# Loaded once at import time so every module sharing this instance
# reuses the same in-memory model instead of reloading it repeatedly.
model = SentenceTransformer("all-MiniLM-L6-v2")


def create_embeddings(chunks):
    """
    Convert a list of text chunks into normalized vector embeddings,
    suitable for cosine-similarity search.
    """
    embeddings = model.encode(
        chunks,
        show_progress_bar=False,
        normalize_embeddings=True,
    )
    return embeddings


def create_query_embedding(query):
    """
    Same embedding space as create_embeddings(), for a single query string.
    """
    return model.encode(
        [query],
        show_progress_bar=False,
        normalize_embeddings=True,
    )[0]