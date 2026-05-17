import os
import psycopg
from typing import List, Dict
from dotenv import load_dotenv
from openai import OpenAI
from sentence_transformers import CrossEncoder

load_dotenv()

EMBEDDING_MODEL = "text-embedding-3-small"
CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

# Refined prompt — grounded, chain-of-thought style for better faithfulness
SYSTEM_PROMPT = """You are StarkBot, an expert assistant on Iron Man and the Marvel universe.
Answer the user's question using ONLY the provided context. If the context is insufficient, say so.
Think step by step: identify the relevant facts in the context, then compose a clear, accurate answer.
Do not fabricate details not present in the context. Do not say "according to the context"."""


class RAGQuerySystem:
    def __init__(self):
        self.openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.chat_model = os.getenv("CHAT_MODEL", "gpt-4o-mini")
        self.reranker = CrossEncoder(CROSS_ENCODER_MODEL)
        self.connection = None
        self._connect()

    def _connect(self):
        try:
            self.connection = psycopg.connect(
                host=os.getenv("DATABASE_HOST"),
                dbname=os.getenv("DATABASE_NAME"),
                user=os.getenv("DATABASE_USER"),
                password=os.getenv("DATABASE_PASSWORD") or None,
            )
            print("✅ Connected to database")
        except psycopg.Error as e:
            print(f"❌ Database connection error: {e}")
            raise

    def _embed(self, text: str) -> List[float]:
        response = self.openai.embeddings.create(input=text, model=EMBEDDING_MODEL)
        return response.data[0].embedding

    def _semantic_search(self, query_embedding: List[float], limit: int = 20) -> List[Dict]:
        embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
        sql = """
            SELECT id, content, source, source_url, embedding <-> %s AS distance
            FROM items
            ORDER BY embedding <-> %s
            LIMIT %s
        """
        with self.connection.cursor() as cur:
            cur.execute(sql, (embedding_str, embedding_str, limit))
            rows = cur.fetchall()
        return [{"id": r[0], "content": r[1], "source": r[2], "source_url": r[3], "distance": r[4]}
                for r in rows]

    def _bm25_search(self, query: str, limit: int = 20) -> List[Dict]:
        sql = """
            SELECT id, content, source, source_url,
                   ts_rank(tsv, plainto_tsquery('english', %s)) AS rank
            FROM items
            WHERE tsv @@ plainto_tsquery('english', %s)
            ORDER BY rank DESC
            LIMIT %s
        """
        try:
            with self.connection.cursor() as cur:
                cur.execute(sql, (query, query, limit))
                rows = cur.fetchall()
            return [{"id": r[0], "content": r[1], "source": r[2], "source_url": r[3], "bm25_rank": r[4]}
                    for r in rows]
        except psycopg.Error:
            return []

    def _rrf(self, semantic: List[Dict], bm25: List[Dict], k: int = 60) -> List[Dict]:
        """Reciprocal Rank Fusion of two ranked lists."""
        scores: Dict[int, Dict] = {}
        for rank, r in enumerate(semantic):
            rid = r["id"]
            if rid not in scores:
                scores[rid] = dict(r)
                scores[rid]["rrf_score"] = 0.0
            scores[rid]["rrf_score"] += 1.0 / (k + rank + 1)

        for rank, r in enumerate(bm25):
            rid = r["id"]
            if rid not in scores:
                scores[rid] = dict(r)
                scores[rid]["rrf_score"] = 0.0
            scores[rid]["rrf_score"] += 1.0 / (k + rank + 1)

        return sorted(scores.values(), key=lambda x: x["rrf_score"], reverse=True)

    def _rerank(self, query: str, candidates: List[Dict], top_n: int = 5) -> List[Dict]:
        """Cross-encoder reranking of fused candidates."""
        if not candidates:
            return []
        pairs = [(query, c["content"]) for c in candidates]
        scores = self.reranker.predict(pairs)
        ranked = sorted(zip(scores, candidates), key=lambda x: x[0], reverse=True)
        return [item for _, item in ranked[:top_n]]

    def retrieve(self, query: str) -> List[Dict]:
        """Full hybrid retrieval pipeline: semantic + BM25 → RRF → cross-encoder."""
        embedding = self._embed(query)
        semantic = self._semantic_search(embedding, limit=20)
        bm25 = self._bm25_search(query, limit=20)
        fused = self._rrf(semantic, bm25)
        return self._rerank(query, fused, top_n=5)

    def generate_response(self, query: str, chunks: List[Dict]) -> str:
        context = "\n\n".join(c["content"] for c in chunks)
        user_msg = f"Context:\n{context}\n\nQuestion: {query}"
        response = self.openai.chat.completions.create(
            model=self.chat_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=500,
            temperature=0.3,
        )
        return response.choices[0].message.content

    def query(self, question: str) -> Dict:
        """Returns {"response": str, "sources": [{"name": str, "url": str}]}"""
        chunks = self.retrieve(question)
        if not chunks:
            return {"response": "I couldn't find relevant information to answer that.", "sources": []}

        answer = self.generate_response(question, chunks)

        seen = set()
        sources = []
        for c in chunks:
            key = c.get("source", "")
            if key and key not in seen:
                seen.add(key)
                sources.append({"name": c["source"], "url": c.get("source_url", "")})

        return {"response": answer, "sources": sources}

    def close(self):
        if self.connection:
            self.connection.close()


def main():
    rag = RAGQuerySystem()
    print("🤖 StarkBot Ready! Ask me anything about Iron Man. Type 'quit' to exit.\n")
    while True:
        question = input("You: ").strip()
        if question.lower() in ("quit", "exit", "bye"):
            print("👋 Goodbye!")
            break
        if not question:
            continue
        result = rag.query(question)
        print(f"🤖 StarkBot: {result['response']}")
        if result["sources"]:
            print("   Sources: " + ", ".join(s["name"] for s in result["sources"]))
        print()
    rag.close()


if __name__ == "__main__":
    main()
