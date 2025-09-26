# api.py
# FastAPI application for Ollama model interactions
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from ollama_interface.client import OllamaClient
from groq_interface.client import GroqClient

# Create a factory function to get the appropriate client
def get_client(client_type: str = "ollama"):
    if client_type.lower() == "ollama":
        return OllamaClient()
    elif client_type.lower() == "groq":
        return GroqClient()
    else:
        raise ValueError(f"Unknown client type: {client_type}")

# Initialize client as None - will be set when app starts
client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global client
    load_dotenv()

    # Set the client based on argument
    client = get_client(os.getenv("LLM_CLIENT", "ollama"))

    yield

    # Cleanup (if needed)
    # Add any cleanup code here

app = FastAPI(lifespan=lifespan)

class PullModelRequest(BaseModel):
    model_name: str

class WarmModelRequest(BaseModel):
    model_name: str

class ChatRequest(BaseModel):
    model_name: str
    messages: List[Dict[str, str]]
    options: Optional[Dict[str, Any]] = None

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/models")
def list_models():
    return client.list_models()

@app.post("/models/pull")
def pull_model(req: PullModelRequest):
    try:
        client.pull_model(req.model_name)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/models/warm")
def warm_model(req: WarmModelRequest):
    try:
        result = client.warm_model(req.model_name)
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/chat")
def chat(req: ChatRequest):
    try:
        response = client.chat(req.model_name, req.messages, req.options)
        return response
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
