# StarkBot

A full-stack RAG chatbot built over 20+ Marvel sources that answers questions about Iron Man and the wider MCU. Features hybrid BM25 + semantic retrieval with cross-encoder reranking, source attribution, and a RAGAS evaluation pipeline.

## Stack

- **Backend**: FastAPI + pgvector (PostgreSQL) + OpenAI
- **Frontend**: React 18
- **Retrieval**: OpenAI `text-embedding-3-small` embeddings + Postgres full-text search (BM25) fused via Reciprocal Rank Fusion, reranked with `cross-encoder/ms-marco-MiniLM-L-6-v2`
- **Eval**: RAGAS (faithfulness, answer relevancy, context precision, context recall)

## Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL with the [pgvector](https://github.com/pgvector/pgvector) extension

### 1. Clone and install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cd frontend && npm install && cd ..
```

### 2. Configure environment

```bash
cp .env.example .env
# Fill in your OPENAI_API_KEY and database credentials
```

### 3. Scrape sources and build the database

```bash
# Download 17 additional Marvel sources (runs once)
python scrape_sources.py

# Migrate DB schema (adds source columns, tsvector, resizes embedding dim)
python migrate_db.py

# Embed all chunks and store in PostgreSQL
python generate_embeddings.py
```

### 4. Run

```bash
# Terminal 1 — backend
.venv/bin/uvicorn app:app --port 8000

# Terminal 2 — frontend
cd frontend && npm start
```

Open `http://localhost:3000`.

## Evaluation

```bash
# Run RAGAS on the full 52-case test suite
python eval/run_eval.py --mode compare

# Quick smoke test (10 cases)
python eval/run_eval.py --mode compare --limit 10
```

Results are saved to `eval/results_<mode>_<timestamp>.json`.

## Data Sources

20 sources across Wikipedia, MCU Fandom, and Marvel.com — covering Iron Man, Tony Stark, armor history, War Machine, Pepper Potts, Avengers films, Civil War, Infinity War, Endgame, supporting characters, and villains.
