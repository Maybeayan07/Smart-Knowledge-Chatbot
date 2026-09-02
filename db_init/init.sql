-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sessions (
    id SERIAL PRIMARY KEY,
    title TEXT DEFAULT 'New Chat',
    user_id INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS doc_chunks (
    id SERIAL PRIMARY KEY,
    text TEXT NOT NULL,
    embedding VECTOR(384),
    session_id INTEGER REFERENCES sessions(id) ON DELETE CASCADE,
    source_file TEXT,
    page_number INTEGER
);

CREATE TABLE IF NOT EXISTS image_chunks (
    id SERIAL PRIMARY KEY,
    path TEXT NOT NULL,
    embedding VECTOR(512),
    session_id INTEGER REFERENCES sessions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS feedback (
    id SERIAL PRIMARY KEY,
    session_id INTEGER,
    question TEXT,
    answer TEXT,
    rating TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS query_log (
    id SERIAL PRIMARY KEY,
    session_id INTEGER,
    question TEXT,
    response_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);