# Smart Knowledge Chatbot

A production-oriented **multimodal Retrieval-Augmented Generation (RAG) chatbot** that allows users to upload documents and images, then ask natural-language questions about their content.

The system combines semantic search, keyword search, reranking, multimodal retrieval, source citations, confidence scoring, authentication, analytics, and conversational features to provide grounded answers from user-provided knowledge.

The architecture is designed so the chatbot can be extended from a general knowledge assistant into a **domain-specific AI support or knowledge-management system for a company or organization**.

---

## ✨ Features

### Core RAG Pipeline

* Upload PDF, DOCX, and TXT documents
* Extract, clean, chunk, and embed document content
* Semantic vector search using PostgreSQL + pgvector
* **Hybrid retrieval** combining vector similarity and BM25 keyword search
* **Cross-encoder reranking** for improved retrieval precision
* **HyDE** for improving retrieval on short or ambiguous queries
* **Query decomposition** for multi-part questions
* Parent-child chunk expansion for better contextual continuity
* File-level and page-level source citations
* Grounded answer generation using retrieved context

### Multimodal Knowledge Retrieval

* Upload and index images
* Image embeddings using OpenCLIP
* Semantic image search
* Combined document and image retrieval
* Automatic query intent routing

### Trust & Answer Quality

* Confidence scoring for generated answers
* Grounded, partially grounded, and low-confidence response states
* Self-checking of generated answers against retrieved context
* Clear responses when requested information is not available
* 👍 / 👎 feedback collection for future evaluation and improvement

### Multilingual Support

* Supports questions in multiple languages
* Query translation can be used during retrieval
* Answers can be generated in the user's original language

### Conversation Features

* Persistent chat sessions
* Separate knowledge base for each session
* Automatic chat title generation
* Edit and regenerate previous questions
* Streaming responses
* Export conversations as PDF or Markdown

### Authentication & Multi-user Support

* JWT-based signup and login
* User-specific sessions
* Isolated document and image knowledge bases
* Protected API routes

### Analytics

* Total queries
* Average response time
* Frequently asked questions
* Feedback statistics
* Indexed document statistics

### Engineering

* Modular FastAPI backend
* PostgreSQL + pgvector database
* Dockerized backend and database environment
* Environment-variable based configuration
* Reproducible local development setup

---

## 🛠 Tech Stack

| Layer               | Technology             |
| ------------------- | ---------------------- |
| Backend             | FastAPI, Python        |
| LLM                 | Groq API               |
| Text Embeddings     | Sentence Transformers  |
| Image Embeddings    | OpenCLIP               |
| Vector Database     | PostgreSQL + pgvector  |
| Keyword Search      | BM25                   |
| Reranking           | Cross-Encoder          |
| Authentication      | JWT, bcrypt            |
| Document Processing | PyMuPDF, python-docx   |
| PDF Export          | ReportLab              |
| Frontend            | HTML, CSS, JavaScript  |
| Containerization    | Docker, Docker Compose |

---

## 🏗 Architecture

```text
                    ┌─────────────────────┐
                    │       User          │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   Frontend UI       │
                    │    HTML / JS / CSS  │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    FastAPI Backend  │
                    └──────────┬──────────┘
                               │
                 ┌─────────────┼─────────────┐
                 ▼             ▼             ▼
          Document/Image    Retrieval      LLM
            Processing       Pipeline     Generation
                 │             │             │
                 │      ┌──────┴──────┐      │
                 │      ▼             ▼      │
                 │   Vector Search   BM25    │
                 │      │             │      │
                 │      └──────┬──────┘      │
                 │             ▼             │
                 │        Reranking          │
                 │             │             │
                 └─────────────┼─────────────┘
                               ▼
                    PostgreSQL + pgvector
```

### RAG Flow

1. User submits a question
2. Query is processed and rewritten when required
3. Multi-part questions can be decomposed into sub-queries
4. Vector and keyword searches retrieve relevant candidates
5. Retrieved results are merged and deduplicated
6. Cross-encoder reranking selects the strongest context
7. Relevant neighboring chunks can be included
8. Groq generates an answer using the retrieved context
9. Source citations and confidence information are attached
10. A self-check can verify the generated answer against the retrieved knowledge

---

## 🚀 Getting Started

### Prerequisites

* Python 3.11+
* Docker & Docker Compose
* Groq API key

### Setup

Clone the repository:

```bash
git clone https://github.com/Maybeayan07/Smart-Knowledge-Chatbot.git
cd Smart-Knowledge-Chatbot
```

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key_here
JWT_SECRET=your_long_random_secret
DB_PASSWORD=your_database_password
```

Build and start the application:

```bash
docker compose up --build
```

Open:

```text
http://127.0.0.1:8000/ui/
```

### Running Without Docker

Create and activate a virtual environment:

```bash
python -m venv venv
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Configure PostgreSQL with the `pgvector` extension and set the required database variables in `.env`.

Run the database schema from:

```text
db_init/init.sql
```

Start the backend:

```bash
uvicorn backend.main:app --reload
```

---

## 📁 Project Structure

```text
Smart-Knowledge-Chatbot/
│
├── backend/
│   ├── main.py
│   ├── chatbot.py
│   ├── auth.py
│   ├── vector_store.py
│   ├── embeddings.py
│   ├── image_processor.py
│   ├── pdf_loader.py
│   ├── text_splitter.py
│   ├── db.py
│   └── config.py
│
├── frontend/
│   ├── index.html
│   ├── script.js
│   └── style.css
│
├── db_init/
│   └── init.sql
│
├── documents/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## 🔑 Environment Variables

| Variable       | Description                               |
| -------------- | ----------------------------------------- |
| `GROQ_API_KEY` | API key used for LLM inference            |
| `JWT_SECRET`   | Secret used to sign authentication tokens |
| `DB_HOST`      | PostgreSQL host                           |
| `DB_PORT`      | PostgreSQL port                           |
| `DB_NAME`      | Database name                             |
| `DB_USER`      | Database username                         |
| `DB_PASSWORD`  | Database password                         |

---

## 📡 Key API Endpoints

| Method | Endpoint        | Description                            |
| ------ | --------------- | -------------------------------------- |
| `POST` | `/signup`       | Create an account                      |
| `POST` | `/login`        | Authenticate a user                    |
| `POST` | `/sessions`     | Create a chat session                  |
| `POST` | `/upload-doc`   | Upload and index a document            |
| `POST` | `/upload-image` | Upload and index an image              |
| `POST` | `/chat-stream`  | Ask a question with streaming response |
| `POST` | `/feedback`     | Submit answer feedback                 |
| `GET`  | `/analytics`    | Retrieve usage analytics               |
| `GET`  | `/export-chat`  | Export a conversation                  |

---

## 🗺 Future Development

The system can be extended beyond a general document-based chatbot into a **specialized AI assistant for real-world organizations**.

Planned directions include:

* [ ] Deploy the system as a publicly accessible cloud application
* [ ] Add an **AI voice agent** for real-time voice-based conversations
* [ ] Integrate voice input/output with the existing RAG pipeline
* [ ] Add a **company-specific dataset and knowledge base**
* [ ] Build specialized versions for domains such as customer support, internal company knowledge, documentation, or product support
* [ ] Allow companies to upload their own manuals, policies, FAQs, product documentation, and internal resources
* [ ] Improve retrieval and answer quality using collected user feedback
* [ ] Add automated evaluation of RAG retrieval and generated answers
* [ ] Add role-based access control for organizational users
* [ ] Support larger-scale document collections and knowledge bases

### Example Future Deployment

```text
Company Knowledge Base
        │
        ├── Product Documentation
        ├── FAQs
        ├── Policies
        ├── Manuals
        └── Support Documents
                │
                ▼
        Smart Knowledge Chatbot
                │
        ┌───────┴────────┐
        ▼                ▼
   Text Chat         Voice Agent
        │                │
        └────────┬───────┘
                 ▼
          Company AI Assistant
```

This would allow the same core system to be adapted into a **company-specific customer support assistant or internal knowledge assistant** rather than remaining limited to a generic document chatbot.

---

## 📄 License

This project is available for learning, experimentation, and further development.

---

## 👤 Author

**Ayan Aleem**

AI Developer | Machine Learning & Computer Vision

Interested in building AI systems involving **RAG, LLMs, Computer Vision, NLP, and intelligent automation**.
