import os
import psycopg
import time
from typing import List
from dotenv import load_dotenv
from openai import OpenAI
from process_data import TextChunk

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
EMBEDDING_MODEL = "text-embedding-3-small"


def generate_embedding(text: str) -> List[float]:
    response = client.embeddings.create(input=text, model=EMBEDDING_MODEL)
    return response.data[0].embedding


def connect_db():
    return psycopg.connect(
        host=os.getenv("DATABASE_HOST"),
        dbname=os.getenv("DATABASE_NAME"),
        user=os.getenv("DATABASE_USER"),
        password=os.getenv("DATABASE_PASSWORD") or None,
    )


def insert_chunk(conn, chunk: TextChunk, embedding: List[float]):
    embedding_str = '[' + ','.join(map(str, embedding)) + ']'
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO items (content, embedding, source, source_url) VALUES (%s, %s, %s, %s)",
            (chunk.content, embedding_str, chunk.source, chunk.source_url),
        )
    conn.commit()


def main():
    from process_data import main as load_chunks
    chunks = load_chunks()
    print(f"\n🚀 Embedding {len(chunks)} chunks with OpenAI {EMBEDDING_MODEL}...")

    conn = connect_db()
    batch_size = 20
    total = len(chunks)

    for i, chunk in enumerate(chunks):
        try:
            embedding = generate_embedding(chunk.content)
            insert_chunk(conn, chunk, embedding)
            if (i + 1) % batch_size == 0 or (i + 1) == total:
                print(f"  [{i + 1}/{total}] ✅ {chunk.source}")
            # OpenAI rate limit: ~3000 RPM on tier-1, ~0.02s between calls is safe
            time.sleep(0.05)
        except Exception as e:
            print(f"  ❌ Chunk {i + 1} failed: {e}")

    conn.close()
    print(f"\n🎉 Done! {total} chunks embedded and stored.")


if __name__ == "__main__":
    main()
