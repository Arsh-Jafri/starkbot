import os
import psycopg
import requests
import json
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

class RAGQuerySystem:
    def __init__(self):
        self.api_key = os.getenv('PWC_API_KEY')
        self.api_base = os.getenv('PWC_API_BASE')
        self.chat_model = os.getenv('CHAT_MODEL')
        self.embedding_model = os.getenv('EMBEDDING_MODEL')
        self.connection = None
        self.connect()
    
    def connect(self):
        """Connect to PostgreSQL database."""
        try:
            password = os.getenv('DATABASE_PASSWORD') or None
            self.connection = psycopg.connect(
                host=os.getenv('DATABASE_HOST'),
                dbname=os.getenv('DATABASE_NAME'),
                user=os.getenv('DATABASE_USER'),
                password=password
            )
            print("✅ Connected to database")
        except psycopg.Error as e:
            print(f"❌ Database connection error: {e}")
            raise
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for query text."""
        url = f"{self.api_base}/v1/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "input": text,
            "model": self.embedding_model,
            "encoding_format": "float",
            "dimensions": 512
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data['data'][0]['embedding']
        except requests.exceptions.RequestException as e:
            print(f"Error generating embedding: {e}")
            return None
    
    def search_similar_chunks(self, query_embedding: List[float], limit: int = 5) -> List[Dict]:
        """Find most similar chunks using vector similarity."""
        try:
            # Convert embedding to PostgreSQL vector format
            embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
            
            # Use cosine similarity to find most relevant chunks
            query = """
            SELECT id, content, embedding <-> %s as distance
            FROM items
            ORDER BY embedding <-> %s
            LIMIT %s
            """
            
            with self.connection.cursor() as cursor:
                cursor.execute(query, (embedding_str, embedding_str, limit))
                results = cursor.fetchall()
            
            return [
                {"id": row[0], "content": row[1], "distance": row[2]}
                for row in results
            ]
            
        except psycopg.Error as e:
            print(f"❌ Search error: {e}")
            return []
    
    def generate_response(self, query: str, context_chunks: List[Dict]) -> str:
        """Generate response using LLM with context."""
        # Prepare context from similar chunks
        context = "\n\n".join([chunk["content"] for chunk in context_chunks])
        
        # Create prompt for StarkBot
        prompt = f"""You are an expert Iron Man chatbot named StarkBot. Answer the user's question based on the provided context about Iron Man. You are not Iron Man or Tony Stark.

Context about Iron Man:
{context}

User Question: {query}

Provide a helpful, accurate answer based on the context. If the context doesn't contain enough information to answer the question, say so politely."""

        url = f"{self.api_base}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.chat_model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 500,
            "temperature": 0.7
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data['choices'][0]['message']['content']
        except requests.exceptions.RequestException as e:
            return f"Error generating response: {e}"
    
    def query(self, question: str) -> str:
        """Main query function - ask a question and get an answer."""
        print(f"🔍 Processing question: {question}")
        
        # Generate embedding for the question
        query_embedding = self.generate_embedding(question)
        if not query_embedding:
            return "❌ Failed to process your question"
        
        # Find similar chunks
        similar_chunks = self.search_similar_chunks(query_embedding, limit=3)
        if not similar_chunks:
            return "❌ No relevant information found"
        
        print(f"📚 Found {len(similar_chunks)} relevant chunks")
        
        # Generate response
        response = self.generate_response(question, similar_chunks)
        return response
    
    def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()

def main():
    """Interactive RAG query system."""
    rag = RAGQuerySystem()
    
    print("🤖 StarBot Ready!")
    print("Ask me anything about Iron Man. Type 'quit' to exit.\n")
    
    while True:
        question = input("You: ").strip()
        
        if question.lower() in ['quit', 'exit', 'bye']:
            print("👋 Goodbye!")
            break
        
        if not question:
            continue
        
        answer = rag.query(question)
        print(f"🤖 Iron Man Bot: {answer}\n")
    
    rag.close()

if __name__ == "__main__":
    main()