import os
import json
import time
import shutil
import uuid

from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel

import joblib

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from backend.pdf_loader import extract_pages_from_file, clean_text
from backend.text_splitter import split_pages_into_chunks
from backend.embeddings import create_embeddings, model as embed_model
from backend.chatbot import answer_question, retrieve_context, build_messages, stream_llm, rewrite_query, compute_confidence, generate_chat_title
from backend.image_processor import process_image, embed_text_query
from backend.vector_store import PgVectorStore
from backend.db import get_connection
from backend import config
from backend.auth import hash_password, verify_password, create_access_token, get_current_user_id

app = FastAPI()
app.mount("/ui", StaticFiles(directory="frontend", html=True), name="frontend")
app.mount("/images", StaticFiles(directory="images"), name="images")

vector_store = PgVectorStore("doc_chunks", "text")
image_store = PgVectorStore("image_chunks", "path")

try:
    intent_classifier = joblib.load("models/intent_classifier.pkl")
except FileNotFoundError:
    intent_classifier = None


class Question(BaseModel):
    question: str
    session_id: int


class FeedbackPayload(BaseModel):
    session_id: int
    question: str
    answer: str
    rating: str  # "up" or "down"


class SignupPayload(BaseModel):
    email: str
    password: str


class LoginPayload(BaseModel):
    email: str
    password: str


# ---------- Session helpers ----------

def create_session(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO sessions (title, user_id) VALUES ('New Chat', %s) RETURNING id", (user_id,))
    session_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return session_id


def get_sessions(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, title, created_at FROM sessions WHERE user_id = %s ORDER BY created_at DESC",
        (user_id,)
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{"id": r[0], "title": r[1], "created_at": r[2].isoformat()} for r in rows]


def delete_session(session_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM doc_chunks WHERE session_id = %s", (session_id,))
    cur.execute("DELETE FROM image_chunks WHERE session_id = %s", (session_id,))
    cur.execute("DELETE FROM messages WHERE session_id = %s", (session_id,))
    cur.execute("DELETE FROM query_log WHERE session_id = %s", (session_id,))
    cur.execute("DELETE FROM feedback WHERE session_id = %s", (session_id,))
    cur.execute("DELETE FROM sessions WHERE id = %s", (session_id,))
    conn.commit()
    cur.close()
    conn.close()

def get_session_messages(session_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, role, content FROM messages WHERE session_id = %s ORDER BY id ASC",
        (session_id,)
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{"id": r[0], "role": r[1], "content": r[2]} for r in rows]


def save_message(session_id, role, content):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO messages (session_id, role, content) VALUES (%s, %s, %s)",
        (session_id, role, content)
    )
    conn.commit()
    cur.close()
    conn.close()


def get_history(session_id, limit=4):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT role, content FROM messages WHERE session_id = %s ORDER BY id DESC LIMIT %s",
        (session_id, limit * 2)
    )
    rows = cur.fetchall()[::-1]
    cur.close()
    conn.close()

    history = []
    i = 0
    while i < len(rows) - 1:
        if rows[i][0] == "user" and rows[i + 1][0] == "assistant":
            history.append({"question": rows[i][1], "answer": rows[i + 1][1]})
            i += 2
        else:
            i += 1
    return history


def maybe_set_title(session_id, question):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT title FROM sessions WHERE id = %s", (session_id,))
    row = cur.fetchone()
    if row and row[0] == "New Chat":
        title = generate_chat_title(question)
        cur.execute("UPDATE sessions SET title = %s WHERE id = %s", (title, session_id))
        conn.commit()
    cur.close()
    conn.close()


# ---------- Routes ----------

@app.get("/")
def home():
    return {"message": "Smart Knowledge Chatbot Backend is Running!"}


# ---------- Auth ----------

@app.post("/signup")
def signup(payload: SignupPayload):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM users WHERE email = %s", (payload.email,))
    if cur.fetchone():
        cur.close()
        conn.close()
        raise HTTPException(status_code=400, detail="Email already registered.")

    hashed = hash_password(payload.password)
    cur.execute(
        "INSERT INTO users (email, hashed_password) VALUES (%s, %s) RETURNING id",
        (payload.email, hashed)
    )
    user_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()

    token = create_access_token({"user_id": user_id, "email": payload.email})
    return {"access_token": token, "token_type": "bearer"}


@app.post("/login")
def login(payload: LoginPayload):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, hashed_password FROM users WHERE email = %s", (payload.email,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row or not verify_password(payload.password, row[1]):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    token = create_access_token({"user_id": row[0], "email": payload.email})
    return {"access_token": token, "token_type": "bearer"}


# ---------- Sessions ----------

@app.post("/sessions")
def new_session(user_id: int = Depends(get_current_user_id)):
    return {"session_id": create_session(user_id)}


@app.get("/sessions")
def list_sessions(user_id: int = Depends(get_current_user_id)):
    return {"sessions": get_sessions(user_id)}


@app.get("/sessions/{session_id}/messages")
def session_messages(session_id: int, user_id: int = Depends(get_current_user_id)):
    return {"messages": get_session_messages(session_id)}


@app.delete("/sessions/{session_id}")
def remove_session(session_id: int, user_id: int = Depends(get_current_user_id)):
    delete_session(session_id)
    return {"message": "deleted"}


@app.delete("/sessions/{session_id}/messages/from/{message_id}")
def delete_messages_from(session_id: int, message_id: int, user_id: int = Depends(get_current_user_id)):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM messages WHERE session_id = %s AND id >= %s",
        (session_id, message_id)
    )
    conn.commit()
    cur.close()
    conn.close()
    return {"message": "deleted"}


@app.get("/status")
def status(session_id: int = Query(...), user_id: int = Depends(get_current_user_id)):
    return {
        "has_doc": vector_store.has_data(session_id),
        "doc_chunks": vector_store.count(session_id),
        "has_images": image_store.has_data(session_id),
        "image_count": image_store.count(session_id),
    }


@app.post("/upload-doc")
async def upload_doc(file: UploadFile = File(...), session_id: int = Query(...), user_id: int = Depends(get_current_user_id)):
    allowed_extensions = (".pdf", ".docx", ".txt")
    if not file.filename.lower().endswith(allowed_extensions):
        raise HTTPException(status_code=400, detail="Only PDF, DOCX, and TXT files are supported.")

    os.makedirs(config.UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(config.UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    pages = extract_pages_from_file(file_path)
    pages = [(pg, clean_text(text)) for pg, text in pages]
    chunk_dicts = split_pages_into_chunks(pages, source_file=file.filename)

    texts = [c["text"] for c in chunk_dicts]
    metadata = [{"source_file": c["source_file"], "page_number": c["page_number"]} for c in chunk_dicts]

    embeddings = create_embeddings(texts)
    vector_store.add_items(embeddings, texts, session_id, metadata=metadata)

    return {"message": f"'{file.filename}' added. Total chunks indexed: {vector_store.count(session_id)}"}


@app.post("/clear-doc")
def clear_doc(session_id: int = Query(...), user_id: int = Depends(get_current_user_id)):
    vector_store.clear(session_id)
    return {"message": "Document knowledge base cleared."}


@app.post("/chat")
def chat(payload: Question, user_id: int = Depends(get_current_user_id)):
    if not vector_store.has_data(payload.session_id):
        raise HTTPException(status_code=400, detail="No document uploaded yet. Upload a PDF first via /upload-doc.")

    history = get_history(payload.session_id)
    answer, _ = answer_question(vector_store, payload.question, payload.session_id, history)

    save_message(payload.session_id, "user", payload.question)
    save_message(payload.session_id, "assistant", answer)
    maybe_set_title(payload.session_id, payload.question)

    return {"answer": answer}


@app.post("/chat-stream")
def chat_stream(payload: Question, user_id: int = Depends(get_current_user_id)):
    if not vector_store.has_data(payload.session_id):
        raise HTTPException(status_code=400, detail="No document uploaded yet. Upload a PDF first via /upload-doc.")

    history = get_history(payload.session_id)

    def generate():
        start_time = time.time()

        rewritten = rewrite_query(payload.question, history)
        context_results = retrieve_context(vector_store, rewritten, payload.session_id)
        confidence_level, confidence_score = compute_confidence(context_results)
        messages = build_messages(payload.question, context_results, confidence_level, history)

        full_answer = ""
        for piece in stream_llm(messages):
            full_answer += piece
            yield piece

        save_message(payload.session_id, "user", payload.question)
        save_message(payload.session_id, "assistant", full_answer)
        maybe_set_title(payload.session_id, payload.question)

        elapsed_ms = int((time.time() - start_time) * 1000)
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO query_log (session_id, question, response_time_ms) VALUES (%s, %s, %s)",
            (payload.session_id, payload.question, elapsed_ms)
        )
        conn.commit()
        cur.close()
        conn.close()

        sources = []
        seen = set()
        for r in context_results:
            key = (r.get("source_file"), r.get("page_number"))
            if key not in seen:
                seen.add(key)
                sources.append({"file": r.get("source_file"), "page": r.get("page_number")})

        payload_data = {
            "sources": sources,
            "confidence": confidence_level
        }
        yield f"\n[[SOURCES]]{json.dumps(payload_data)}"

    return StreamingResponse(generate(), media_type="text/plain")


@app.post("/feedback")
def submit_feedback(payload: FeedbackPayload, user_id: int = Depends(get_current_user_id)):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO feedback (session_id, question, answer, rating) VALUES (%s, %s, %s, %s)",
        (payload.session_id, payload.question, payload.answer, payload.rating)
    )
    conn.commit()
    cur.close()
    conn.close()
    return {"message": "Feedback recorded"}


@app.get("/analytics")
def get_analytics(user_id: int = Depends(get_current_user_id)):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM query_log")
    total_queries = cur.fetchone()[0]

    cur.execute("SELECT AVG(response_time_ms) FROM query_log")
    avg_time = cur.fetchone()[0]
    avg_time = round(avg_time) if avg_time else 0

    cur.execute("""
        SELECT question, COUNT(*) as cnt FROM query_log
        GROUP BY question ORDER BY cnt DESC LIMIT 5
    """)
    top_questions = [{"question": r[0], "count": r[1]} for r in cur.fetchall()]

    cur.execute("SELECT rating, COUNT(*) FROM feedback GROUP BY rating")
    feedback_rows = cur.fetchall()
    feedback_counts = {"up": 0, "down": 0}
    for rating, count in feedback_rows:
        feedback_counts[rating] = count

    cur.execute("SELECT COUNT(DISTINCT source_file) FROM doc_chunks WHERE source_file IS NOT NULL")
    doc_count = cur.fetchone()[0]

    cur.close()
    conn.close()

    return {
        "total_queries": total_queries,
        "avg_response_time_ms": avg_time,
        "top_questions": top_questions,
        "feedback": feedback_counts,
        "documents_indexed": doc_count
    }


@app.get("/export-chat")
def export_chat(session_id: int = Query(...), format: str = Query("markdown"), user_id: int = Depends(get_current_user_id)):
    messages = get_session_messages(session_id)
    if not messages:
        raise HTTPException(status_code=400, detail="No messages in this chat to export.")

    os.makedirs("exports", exist_ok=True)

    if format == "markdown":
        file_path = f"exports/chat_{session_id}.md"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"# Chat Export — Session {session_id}\n\n")
            for m in messages:
                role_label = "**You**" if m["role"] == "user" else "**Assistant**"
                f.write(f"{role_label}:\n\n{m['content']}\n\n---\n\n")
        return FileResponse(file_path, filename=f"chat_{session_id}.md", media_type="text/markdown")

    elif format == "pdf":
        file_path = f"exports/chat_{session_id}.pdf"
        doc = SimpleDocTemplate(file_path, pagesize=A4)
        styles = getSampleStyleSheet()

        user_style = ParagraphStyle("UserStyle", parent=styles["Normal"], textColor="#4338ca", spaceAfter=6, fontSize=11)
        bot_style = ParagraphStyle("BotStyle", parent=styles["Normal"], textColor="#111827", spaceAfter=14, fontSize=11)

        story = [Paragraph(f"Chat Export — Session {session_id}", styles["Title"]), Spacer(1, 0.3 * inch)]

        for m in messages:
            label = "You" if m["role"] == "user" else "Assistant"
            style = user_style if m["role"] == "user" else bot_style
            safe_content = m["content"].replace("\n", "<br/>")
            story.append(Paragraph(f"<b>{label}:</b> {safe_content}", style))

        doc.build(story)
        return FileResponse(file_path, filename=f"chat_{session_id}.pdf", media_type="application/pdf")

    else:
        raise HTTPException(status_code=400, detail="format must be 'markdown' or 'pdf'.")


@app.post("/upload-image")
async def upload_image(file: UploadFile = File(...), session_id: int = Query(...), user_id: int = Depends(get_current_user_id)):
    os.makedirs("images", exist_ok=True)
    unique_name = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = os.path.join("images", unique_name)

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    result = process_image(file_path)  # {"embedding": ..., "ocr_text": ...}
    image_store.add_items(
        [result["embedding"]], [file_path], session_id,
        metadata=[{"ocr_text": result["ocr_text"]}]
    )

    message = f"'{file.filename}' indexed successfully."
    if result["ocr_text"]:
        message += " Text detected inside the image (e.g. certificate text) was also indexed for search."

    return {"message": message}


@app.post("/clear-images")
def clear_images(session_id: int = Query(...), user_id: int = Depends(get_current_user_id)):
    image_store.clear(session_id)
    return {"message": "Image index cleared."}


@app.post("/search-image")
def search_image(payload: Question, user_id: int = Depends(get_current_user_id)):
    if not image_store.has_data(payload.session_id):
        raise HTTPException(status_code=400, detail="No images uploaded yet. Upload one first via /upload-image.")

    query_embedding = embed_text_query(payload.question)
    visual_results = image_store.search(query_embedding, payload.session_id, k=3)

    text_results = image_store.search_by_text("ocr_text", payload.question, payload.session_id, k=3)

    merged = {r["chunk_id"]: r for r in visual_results}
    for r in text_results:
        merged[r["chunk_id"]] = r
    combined = list(merged.values())

    save_message(payload.session_id, "user", payload.question)
    maybe_set_title(payload.session_id, payload.question)

    return {"matches": [r["text"] for r in combined]}


@app.post("/predict-intent")
def predict_intent(payload: Question, user_id: int = Depends(get_current_user_id)):
    if intent_classifier is None:
        raise HTTPException(status_code=500, detail="Intent classifier not trained yet.")

    embedding = embed_model.encode([payload.question])
    prediction = intent_classifier.predict(embedding)[0]

    return {"intent": prediction}