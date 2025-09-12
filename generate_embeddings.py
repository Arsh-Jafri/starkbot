import os
import sys
import psycopg
import requests
import json
import time
from typing import List
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class TextChunk:
    content: str
    source: str
    chunk_id: int
    start_char: int
    end_char: int
    metadata: dict

class EmbeddingGenerator:
    def __init__(self):
        self.api_key = os.getenv('PWC_API_KEY')
        self.api_base = os.getenv('PWC_API_BASE')
        self.embedding_model = os.getenv('EMBEDDING_MODEL')
        
        if not all([self.api_key, self.api_base, self.embedding_model]):
            raise ValueError("Missing required environment variables")
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text chunk."""
        url = f"{self.api_base}/v1/embeddings"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "input": text,
            "model": self.embedding_model,
            "encoding_format": "float",
            "dimensions": 512  # This is the key addition!
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            data = response.json()
            return data['data'][0]['embedding']
            
        except requests.exceptions.RequestException as e:
            print(f"Error generating embedding: {e}")
            return None

class DatabaseManager:
    def __init__(self):
        self.connection = None
        self.connect()
    
    def connect(self):
        """Connect to PostgreSQL database."""
        try:
            # Handle empty password
            password = os.getenv('DATABASE_PASSWORD') or None
            
            self.connection = psycopg.connect(
                host=os.getenv('DATABASE_HOST'),
                dbname=os.getenv('DATABASE_NAME'),
                user=os.getenv('DATABASE_USER'),
                password=password
            )
            print("✅ Connected to PostgreSQL database")
        except psycopg.Error as e:
            print(f"❌ Error connecting to database: {e}")
            raise
    
    def insert_chunk_with_embedding(self, chunk: TextChunk, embedding: List[float]):
        """Insert a chunk and its embedding into the database."""
        try:
            # Convert embedding to PostgreSQL vector format
            embedding_str = '[' + ','.join(map(str, embedding)) + ']'
            
            # Simple query without metadata
            query = """
            INSERT INTO items (content, embedding)
            VALUES (%s, %s)
            """
            
            with self.connection.cursor() as cursor:
                cursor.execute(query, (chunk.content, embedding_str))
                self.connection.commit()
            
        except psycopg.Error as e:
            print(f"❌ Error inserting chunk: {e}")
            self.connection.rollback()
            raise
    
    def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()

def load_chunks_from_previous_run():
    """Load chunks from the previous process_data.py run."""
    # Import and run the chunking process
    from process_data import main
    return main()

def main():
    """Generate embeddings and store in database."""
    print("🚀 Starting embedding generation...")
    
    # Load chunks
    print("📖 Loading text chunks...")
    chunks = load_chunks_from_previous_run()
    print(f"Loaded {len(chunks)} chunks")
    
    # Initialize services
    embedding_gen = EmbeddingGenerator()
    db_manager = DatabaseManager()
    
    # Process chunks in batches
    batch_size = 10
    total_chunks = len(chunks)
    
    print(f"🔄 Processing {total_chunks} chunks in batches of {batch_size}...")
    
    for i in range(0, total_chunks, batch_size):
        batch = chunks[i:i + batch_size]
        print(f"Processing batch {i//batch_size + 1}/{(total_chunks + batch_size - 1)//batch_size}")
        
        for j, chunk in enumerate(batch):
            print(f"  Chunk {i + j + 1}/{total_chunks} - {chunk.source}")
            
            # Generate embedding
            embedding = embedding_gen.generate_embedding(chunk.content)
            
            if embedding:
                # Store in database
                db_manager.insert_chunk_with_embedding(chunk, embedding)
                print(f"    ✅ Stored chunk {i + j + 1}")
            else:
                print(f"    ❌ Failed to generate embedding for chunk {i + j + 1}")
            
            # Rate limiting - be nice to the API
            time.sleep(0.1)
        
        # Longer pause between batches
        time.sleep(1)
    
    db_manager.close()
    print("🎉 Embedding generation complete!")

if __name__ == "__main__":
    main()
