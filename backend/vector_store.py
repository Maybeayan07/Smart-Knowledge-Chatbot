import numpy as np

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
            f"SELECT {cols}, embedding <-> %s AS distance FROM {self.table_name} "
            f"WHERE session_id = %s "
            f"ORDER BY embedding <-> %s LIMIT %s",
            (query_embedding, session_id, query_embedding, k)
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()

        results = []
        for row in rows:
            result = {"chunk_id": row[0], "text": row[1]}
            offset = 2
            if extra_columns:
                for idx, col in enumerate(extra_columns):
                    result[col] = row[offset + idx]
                offset += len(extra_columns)
            result["distance"] = row[offset]
            results.append(result)
        return results

    @staticmethod
    def _to_array(v):
        # pgvector returns a Vector object, not a plain list/array — unwrap
        # it safely regardless of which form the driver gives us.
        if hasattr(v, "to_list"):
            return np.asarray(v.to_list(), dtype=np.float32)
        return np.asarray(list(v), dtype=np.float32)

    def search_with_confidence(self, query_embedding, session_id, logit_scale,
                                confidence_threshold=0.4, min_similarity=0.2,
                                extra_columns=None):
        """
        Relative-confidence search: instead of an absolute distance cutoff
        (unreliable — CLIP's raw distances aren't consistently calibrated
        across queries), this scores EVERY image in the session against the
        query, converts cosine similarities into a proper probability
        distribution via softmax (using CLIP's own logit_scale, the same
        mechanism CLIP uses for zero-shot classification), and keeps only
        the images that dominate that distribution.

        min_similarity is a floor to guard the degenerate single-image-
        session case, where softmax alone would always assign 100%
        confidence to the only candidate even if it's irrelevant.
        """
        conn = get_connection()
        cur = conn.cursor()

        cols = f"id, {self.content_column}, embedding"
        if extra_columns:
            cols += ", " + ", ".join(extra_columns)

        cur.execute(
            f"SELECT {cols} FROM {self.table_name} WHERE session_id = %s",
            (session_id,)
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()

        if not rows:
            return []

        query_vec = self._to_array(query_embedding)
        embeddings = np.array([self._to_array(row[2]) for row in rows])

        # Both sides are already unit-normalized, so the dot product IS the
        # cosine similarity — no need for a separate normalization step.
        similarities = embeddings @ query_vec

        logits = similarities * logit_scale
        exp_logits = np.exp(logits - np.max(logits))  # numerically stable softmax
        probabilities = exp_logits / exp_logits.sum()

        results = []
        for row, sim, prob in zip(rows, similarities, probabilities):
            if prob >= confidence_threshold and sim >= min_similarity:
                result = {"chunk_id": row[0], "text": row[1], "confidence": float(prob)}
                if extra_columns:
                    for idx, col in enumerate(extra_columns):
                        result[col] = row[3 + idx]
                results.append(result)

        results.sort(key=lambda r: r["confidence"], reverse=True)
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