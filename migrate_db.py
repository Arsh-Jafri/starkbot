"""
One-time DB migration: adds source/source_url columns, adds tsvector for BM25,
resizes embedding column from 512 → 1536 dims for OpenAI text-embedding-3-small,
and clears old data so we can re-embed everything.
"""
import os
import psycopg
from dotenv import load_dotenv

load_dotenv()


def connect():
    return psycopg.connect(
        host=os.getenv("DATABASE_HOST"),
        dbname=os.getenv("DATABASE_NAME"),
        user=os.getenv("DATABASE_USER"),
        password=os.getenv("DATABASE_PASSWORD") or None,
    )


def main():
    print("🔧 Running database migration...")
    conn = connect()

    with conn.cursor() as cur:
        # Add source columns if missing
        cur.execute("""
            ALTER TABLE items
                ADD COLUMN IF NOT EXISTS source TEXT,
                ADD COLUMN IF NOT EXISTS source_url TEXT;
        """)
        print("  ✅ source / source_url columns added")

        # Clear old data — embeddings are 512-dim and must be regenerated at 1536
        cur.execute("TRUNCATE TABLE items RESTART IDENTITY;")
        print("  ✅ Old rows cleared (will re-embed with OpenAI 1536-dim vectors)")

        # Resize embedding column to 1536
        cur.execute("ALTER TABLE items ALTER COLUMN embedding TYPE vector(1536);")
        print("  ✅ embedding column resized to vector(1536)")

        # Add generated tsvector column for BM25 full-text search
        cur.execute("""
            ALTER TABLE items
                ADD COLUMN IF NOT EXISTS tsv tsvector
                GENERATED ALWAYS AS (to_tsvector('english', coalesce(content, ''))) STORED;
        """)
        print("  ✅ tsv column added (generated tsvector)")

        # GIN index for fast full-text search
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_items_tsv ON items USING GIN(tsv);
        """)
        print("  ✅ GIN index created on tsv")

        # HNSW index on embedding for fast ANN search (pgvector)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_items_embedding
                ON items USING hnsw (embedding vector_cosine_ops);
        """)
        print("  ✅ HNSW index created on embedding")

        conn.commit()

    conn.close()
    print("\n🎉 Migration complete!")


if __name__ == "__main__":
    main()
