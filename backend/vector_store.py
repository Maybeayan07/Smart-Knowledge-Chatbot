from backend.db import get_connection


class PgVectorStore:
    """
    Session-scoped vector store backed by PostgreSQL + pgvector.
    Every method takes session_id so each chat only sees its own data.
    """

    def __init__(self, table_name, content_column):
        self.table_name = table_name
        self.content_column = content_column

    def add_items(self, embeddings, items, session_id, metadata=None):
        conn = get_connection()
        cur = conn.cursor()

        for i, (embedding, item) in enumerate(zip(embeddings, items)):
            if metadata:
                meta = metadata[i]
                columns = ", ".join(meta.keys())
                placeholders = ", ".join(["%s"] * len(meta))
                cur.execute(
                    f"INSERT INTO {self.table_name} "
                    f"({self.content_column}, embedding, session_id, {columns}) "
                    f"VALUES (%s, %s, %s, {placeholders})",
                    (item, embedding, session_id, *meta.values())
                )
            else:
                cur.execute(
                    f"INSERT INTO {self.table_name} ({self.content_column}, embedding, session_id) "
                    f"VALUES (%s, %s, %s)",
                    (item, embedding, session_id)
                )

        conn.commit()
        cur.close()
        conn.close()

    def search(self, query_embedding, session_id, k=3, extra_columns=None):
        conn = get_connection()
        cur = conn.cursor()

        cols = f"id, {self.content_column}"
        if extra_columns:
            cols += ", " + ", ".join(extra_columns)

        cur.execute(
            f"SELECT {cols} FROM {self.table_name} "
            f"WHERE session_id = %s "
            f"ORDER BY embedding <-> %s LIMIT %s",
            (session_id, query_embedding, k)
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()

        results = []
        for row in rows:
            result = {"chunk_id": row[0], "text": row[1]}
            if extra_columns:
                for idx, col in enumerate(extra_columns):
                    result[col] = row[2 + idx]
            results.append(result)
        return results

    def search_by_text(self, text_column, query, session_id, k=3, extra_columns=None):
        """
        Keyword search (ILIKE) on a specific text column — e.g. ocr_text on
        image_chunks — for exact-ish matches embeddings alone tend to miss
        (names, ID numbers, dates on a certificate).
        """
        conn = get_connection()
        cur = conn.cursor()

        cols = f"id, {self.content_column}, {text_column}"
        if extra_columns:
            cols += ", " + ", ".join(extra_columns)

        cur.execute(
            f"SELECT {cols} FROM {self.table_name} "
            f"WHERE session_id = %s AND {text_column} ILIKE %s "
            f"LIMIT %s",
            (session_id, f"%{query}%", k)
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()

        results = []
        for row in rows:
            result = {"chunk_id": row[0], "text": row[1], text_column: row[2]}
            if extra_columns:
                for idx, col in enumerate(extra_columns):
                    result[col] = row[3 + idx]
            results.append(result)
        return results

    def get_all_chunks(self, session_id, extra_columns=None):
        conn = get_connection()
        cur = conn.cursor()

        cols = f"id, {self.content_column}"
        if extra_columns:
            cols += ", " + ", ".join(extra_columns)

        cur.execute(
            f"SELECT {cols} FROM {self.table_name} WHERE session_id = %s",
            (session_id,)
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()

        results = []
        for row in rows:
            result = {"chunk_id": row[0], "text": row[1]}
            if extra_columns:
                for idx, col in enumerate(extra_columns):
                    result[col] = row[2 + idx]
            results.append(result)
        return results

    def count(self, session_id):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM {self.table_name} WHERE session_id = %s", (session_id,))
        result = cur.fetchone()[0]
        cur.close()
        conn.close()
        return result

    def has_data(self, session_id):
        return self.count(session_id) > 0

    def clear(self, session_id):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(f"DELETE FROM {self.table_name} WHERE session_id = %s", (session_id,))
        conn.commit()
        cur.close()
        conn.close()