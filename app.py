from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from query_rag import RAGQuerySystem

app = FastAPI(title="StarkBot API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rag_system = None


class ChatRequest(BaseModel):
    message: str


class Source(BaseModel):
    name: str
    url: str


class ChatResponse(BaseModel):
    response: str
    sources: List[Source] = []


@app.on_event("startup")
async def startup_event():
    global rag_system
    try:
        rag_system = RAGQuerySystem()
        print("✅ RAG system initialized")
    except Exception as e:
        print(f"❌ Failed to initialize RAG system: {e}")


@app.get("/")
async def root():
    return {"message": "StarkBot API is running!"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if rag_system is None:
        raise HTTPException(status_code=500, detail="RAG system not initialized")
    try:
        result = rag_system.query(request.message)
        return ChatResponse(
            response=result["response"],
            sources=[Source(**s) for s in result["sources"]],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    global rag_system
    if rag_system:
        rag_system.close()
