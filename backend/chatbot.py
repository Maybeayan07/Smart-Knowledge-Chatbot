import os
import re
import json
from dotenv import load_dotenv
from groq import Groq

from backend.pdf_loader import extract_text_from_file, clean_text
from backend.text_splitter import split_text_into_chunks
from backend.embeddings import create_embeddings, model

from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder

load_dotenv()
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

MODEL_NAME = "openai/gpt-oss-20b"

SYSTEM_PROMPT = """You are a knowledgeable, precise assistant that answers questions strictly using the document context provided to you. You sound natural and conversational — not robotic — while staying fully grounded in the given context.

Rules:
- Never invent facts that aren't in the context.
- If the context doesn't contain the answer, say so plainly in one sentence, then optionally suggest what related info IS available in the context (if anything close exists).
- Resolve pronouns ("it", "that", "this") using the conversation history.
- For a general/summary question ("what is this document", "summarize this"), open by naming the document type and its subject/owner before details.
- Use a), b), c)... lettered lists only when there are genuinely multiple distinct points. Otherwise answer in plain prose.
- Be concise. Don't pad answers with filler like "Based on the context provided" or "As an AI".
- ALWAYS answer in the same language the user's question was asked in — even though the document context below may be in English, translate the relevant facts naturally into the user's language. Do not mix languages in one answer.
"""

# Common reference words that signal a question depends on prior conversation
# turns (used to skip an unnecessary rewrite/translation LLM call for simple,
# already-English, standalone questions — cuts latency).
_REFERENCE_WORDS = {"it", "that", "this", "those", "these", "they", "them", "he", "she", "his", "her"}

_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "of", "in", "on", "at", "to", "for", "and", "or", "but", "with",
    "this", "that", "these", "those", "it", "as", "by", "from", "into",
    "do", "does", "did", "has", "have", "had", "not", "no", "so",
}


def _is_ascii(text):
    try:
        text.encode("ascii")
        return True
    except UnicodeEncodeError:
        return False


def _tokenize(text):
    """Regex-based tokenizer for BM25 — strips punctuation and stopwords
    for cleaner keyword matching than a plain .split()."""
    words = re.findall(r"[a-zA-Z0-9']+", text.lower())
    return [w for w in words if w not in _STOPWORDS and len(w) > 1]


def rewrite_query(question, history):
    """
    Resolves pronouns using history AND translates the question to English
    for retrieval — the document embeddings are English-based, so a
    non-English query (e.g. Urdu) needs to be translated first for
    semantic search and keyword matching to work well. The final answer
    is still generated in the user's original language (see build_messages).

    Skips the LLM call entirely (fast path) when the question is already
    plain ASCII/English and there's no conversation history to resolve
    references against — avoids unnecessary latency on simple questions.
    """
    has_reference_word = any(w in _REFERENCE_WORDS for w in re.findall(r"[a-zA-Z']+", question.lower()))
    if not history and _is_ascii(question) and not has_reference_word:
        return question

    turns = ""
    if history:
        turns = "\n".join(f"User: {h['question']}\nAssistant: {h['answer']}" for h in history[-4:])

    messages = [
        {
            "role": "system",
            "content": (
                "You rewrite a question into a fully standalone, ENGLISH search "
                "query — resolve pronouns/implicit references using the conversation "
                "history if given, and translate to English if the question is in "
                "another language. Output ONLY the rewritten English query, nothing else."
            ),
        },
        {
            "role": "user",
            "content": f"Conversation so far:\n{turns if turns else '(none)'}\n\nQuestion: \"{question}\"\n\nStandalone English search query:",
        },
    ]

    response = groq_client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=0,
    )
    return response.choices[0].message.content.strip()


def decompose_query(question):
    """
    Splits a multi-part question ("What's X's salary and department?") into
    separate focused sub-queries so each part gets its own retrieval pass.
    Returns [question] unchanged for simple, single-part questions (cheap
    heuristic gate to avoid an LLM call on most questions).
    """
    looks_multi_part = (
        len(question.split()) > 6
        and (question.count("?") > 1 or " and " in question.lower() or ";" in question)
    )
    if not looks_multi_part:
        return [question]

    try:
        response = groq_client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "If the question contains multiple distinct sub-questions, split "
                        "it into separate standalone English questions. If it's really just "
                        "one question, return it as a single-item list. "
                        'Output ONLY a JSON array of strings, e.g. ["question 1", "question 2"]. '
                        "No other text."
                    ),
                },
                {"role": "user", "content": question},
            ],
            temperature=0,
        )
        raw = response.choices[0].message.content.strip()
        raw = re.sub(r"^```(json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
        sub_queries = json.loads(raw)
        if isinstance(sub_queries, list) and all(isinstance(q, str) for q in sub_queries) and sub_queries:
            return sub_queries[:4]
    except Exception:
        pass
    return [question]


def generate_hypothetical_answer(question):
    """
    HyDE (Hypothetical Document Embeddings): generates a short hypothetical
    passage that WOULD answer the question, then that passage — not the raw
    question — is embedded for vector search. A hypothetical answer's
    vocabulary tends to resemble the real document far more than a short
    question does, which noticeably improves retrieval for terse queries
    like "what's the salary?". Falls back to the plain question on any error.
    """
    try:
        response = groq_client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Write a short (2-3 sentence) hypothetical passage that would "
                        "plausibly answer this question, as if it were an excerpt from "
                        "the source document. Don't hedge or say you don't know — just "
                        "write a plausible-sounding passage. Output ONLY the passage."
                    ),
                },
                {"role": "user", "content": question},
            ],
            temperature=0.4,
        )
        text = response.choices[0].message.content.strip()
        return text if text else question
    except Exception:
        return question


def _expand_with_neighbors(candidates, all_chunks):
    """
    Parent-child context expansion: for each selected chunk, pulls in its
    immediate neighboring chunks (same source_file, adjacent chunk_id) so
    the model sees continuous context instead of an isolated fragment —
    reduces answers that feel cut off mid-thought.
    """
    by_id = {c["chunk_id"]: c for c in all_chunks}
    included_ids = {c["chunk_id"] for c in candidates}
    expanded = list(candidates)

    for c in candidates:
        source = c.get("source_file")
        for neighbor_id in (c["chunk_id"] - 1, c["chunk_id"] + 1):
            neighbor = by_id.get(neighbor_id)
            if (
                neighbor
                and neighbor_id not in included_ids
                and neighbor.get("source_file") == source
            ):
                expanded.append(neighbor)
                included_ids.add(neighbor_id)

    return expanded


def retrieve_context(store, question, session_id, k=3):
    all_chunks = store.get_all_chunks(session_id, extra_columns=["source_file", "page_number"])
    if not all_chunks:
        return []

    # Query decomposition — split multi-part questions into sub-queries
    sub_queries = decompose_query(question)

    # HyDE — embed a hypothetical answer alongside the real query for better
    # semantic recall on short/terse questions
    hyde_text = generate_hypothetical_answer(question)
    search_texts = list(dict.fromkeys(sub_queries + [hyde_text]))  # dedup, keep order

    vector_results = {}
    for text in search_texts:
        query_embedding = model.encode(text)
        for r in store.search(
            query_embedding, session_id, k=8,
            extra_columns=["source_file", "page_number"]
        ):
            vector_results[r["chunk_id"]] = r

    # BM25 keyword search (tokenized with stopword removal), against the
    # original (translated) question — not the HyDE passage
    tokenized_corpus = [_tokenize(c["text"]) for c in all_chunks]
    bm25 = BM25Okapi(tokenized_corpus)
    tokenized_query = _tokenize(question)
    scores = bm25.get_scores(tokenized_query)
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:10]
    bm25_results = [all_chunks[i] for i in top_indices if scores[i] > 0]

    merged = dict(vector_results)
    for r in bm25_results:
        merged[r["chunk_id"]] = r
    candidates = list(merged.values())

    if not candidates:
        return []

    # Rerank all merged candidates against the original question
    pairs = [[question, c["text"]] for c in candidates]
    rerank_scores = reranker.predict(pairs)
    for c, score in zip(candidates, rerank_scores):
        c["rerank_score"] = float(score)
    candidates.sort(key=lambda c: c["rerank_score"], reverse=True)

    # Dynamic k — a strong top match needs fewer supporting chunks than a
    # weak/scattered one
    top_score = candidates[0]["rerank_score"]
    if top_score >= 1.0:
        final_k = min(k, 2) if k else 2
    elif top_score >= -1.0:
        final_k = k if k else 4
    else:
        final_k = max(k, 6)

    top_candidates = candidates[:final_k]

    return _expand_with_neighbors(top_candidates, all_chunks)


def compute_confidence(context_results):
    if not context_results:
        return "no_context", 0.0

    scores = [c.get("rerank_score", 0) for c in context_results]
    top_score = max(scores)

    if top_score >= 1.0:
        return "high", top_score
    elif top_score >= -2.0:
        return "medium", top_score
    else:
        return "low", top_score


def generate_chat_title(question):
    try:
        response = groq_client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": "Generate a short, clean title (3-6 words) summarizing this question. No punctuation, no quotes, no 'Title:' prefix. Output ONLY the title."
                },
                {"role": "user", "content": question}
            ],
            temperature=0.3,
        )
        title = response.choices[0].message.content.strip().strip('"').strip("'").rstrip(".")
        return title[:60] if title else question[:50]
    except Exception:
        return question[:50]


def build_messages(question, context_results, confidence, history=None):
    context = "\n\n".join(
        f"[Source: {r.get('source_file', 'document')}"
        f"{', page ' + str(r['page_number']) if r.get('page_number') else ''}]\n{r['text']}"
        for r in context_results
    )

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if history:
        for h in history[-4:]:
            messages.append({"role": "user", "content": h["question"]})
            messages.append({"role": "assistant", "content": h["answer"]})

    if confidence == "no_context":
        guidance = "No relevant context was retrieved. Tell the user there is no information about this in the uploaded document(s), in one natural sentence. Do not guess."
    elif confidence == "low":
        guidance = "The retrieved context is weakly related at best. If it doesn't actually answer the question, say there is no information about this in the uploaded document(s) instead of guessing from a weak match."
    else:
        guidance = "The retrieved context is relevant. Answer directly and naturally from it."

    user_content = f"""Context:
{context if context else "(no context retrieved)"}

Instruction: {guidance}

Question: {question}"""

    messages.append({"role": "user", "content": user_content})
    return messages


def ask_llm(messages, model_name=MODEL_NAME):
    response = groq_client.chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=0.3,
    )
    return response.choices[0].message.content


def stream_llm(messages, model_name=MODEL_NAME):
    stream = groq_client.chat.completions.create(
        model=model_name,
        messages=messages,
        stream=True,
        temperature=0.3,
    )
    for chunk in stream:
        piece = chunk.choices[0].delta.content
        if piece:
            yield piece


def self_check_answer(question, answer, context_results):
    """
    A lightweight second pass that asks the model to verify its own answer
    is actually supported by the retrieved context — catches hallucinated
    claims before they reach the user. Only used for the non-streaming
    /chat path (a streaming answer is already sent by the time this could
    run, so it can't intervene there). Fails open (keeps the original
    answer) on any error so this never breaks a working response.
    """
    if not context_results:
        return answer

    context = "\n\n".join(r["text"] for r in context_results)
    try:
        response = groq_client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You check whether an AI-generated answer is actually supported "
                        "by the given context. Reply with ONLY 'GROUNDED' if every claim "
                        "in the answer is supported by the context, or 'UNGROUNDED' if the "
                        "answer contains claims not present in the context."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Context:\n{context}\n\nQuestion: {question}\n\nAnswer to check:\n{answer}\n\nVerdict:",
                },
            ],
            temperature=0,
        )
        verdict = response.choices[0].message.content.strip().upper()
        if "UNGROUNDED" in verdict:
            return "There is no information about this in the uploaded document."
        return answer
    except Exception:
        return answer


def answer_question(store, question, session_id, history=None):
    rewritten = rewrite_query(question, history)
    context_results = retrieve_context(store, rewritten, session_id)
    confidence, score = compute_confidence(context_results)
    messages = build_messages(question, context_results, confidence, history)
    answer = ask_llm(messages)
    answer = self_check_answer(question, answer, context_results)
    source_ids = [r["chunk_id"] for r in context_results]
    return answer, source_ids


def stream_answer_question(store, question, session_id, history=None):
    rewritten = rewrite_query(question, history)
    context_results = retrieve_context(store, rewritten, session_id)
    confidence, score = compute_confidence(context_results)
    messages = build_messages(question, context_results, confidence, history)
    source_ids = [r["chunk_id"] for r in context_results]
    return stream_llm(messages), source_ids