"""
RAG (Retrieval-Augmented Generation) for the medical chatbot.
Uses Gemini embeddings and DocumentChunk model for a knowledge base.
"""
import json
import math
from django.conf import settings
from .models import DocumentChunk

# Lazy init to avoid import-time API calls
_genai = None
_embedding_model = None


def _get_genai():
    global _genai
    if _genai is None:
        import google.generativeai as genai
        api_key = getattr(settings, "GOOGLE_API_KEY", None)
        if api_key:
            genai.configure(api_key=api_key)
        _genai = genai
    return _genai


def embed_text(text, task_type="retrieval_document"):
    """
    Get embedding for a single text using Gemini embedding model.
    task_type: 'retrieval_document' for indexing, 'retrieval_query' for queries.
    """
    genai = _get_genai()
    if not getattr(settings, "GOOGLE_API_KEY", None):
        return None
    try:
        result = genai.embed_content(
            model="models/embedding-001",
            content=text,
            task_type=task_type,
        )
        if result and "embedding" in result:
            return result["embedding"]
        return None
    except Exception as e:
        print(f"RAG embed_text error: {e}")
        return None


def embed_query(text):
    """Embed a user query for retrieval (use retrieval_query task)."""
    return embed_text(text, task_type="retrieval_query")


def cosine_similarity(a, b):
    """Compute cosine similarity between two vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def retrieve(user_query, top_k=5, min_score=0.0):
    """
    Retrieve top_k most relevant document chunks for the user query.
    Returns list of (chunk, score) with score >= min_score.
    """
    query_embedding = embed_query(user_query)
    if not query_embedding:
        return []

    chunks = DocumentChunk.objects.filter(embedding_json__isnull=False).exclude(embedding_json="")
    if not chunks.exists():
        return []

    scored = []
    for chunk in chunks:
        try:
            emb = json.loads(chunk.embedding_json)
        except (json.JSONDecodeError, TypeError):
            continue
        score = cosine_similarity(query_embedding, emb)
        if score >= min_score:
            scored.append((chunk, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]


def build_rag_context(retrieved):
    """Format retrieved chunks into a single context string for the prompt."""
    if not retrieved:
        return ""
    parts = []
    for i, (chunk, score) in enumerate(retrieved, 1):
        parts.append(f"[{i}] (Source: {chunk.source})\n{chunk.text}")
    return "\n\n---\n\n".join(parts)


def get_rag_context_for_query(user_query, top_k=5):
    """
    One-shot: retrieve chunks for query and return formatted context.
    Returns (context_string, list of (chunk, score)).
    """
    retrieved = retrieve(user_query, top_k=top_k)
    context = build_rag_context(retrieved)
    return context, retrieved
