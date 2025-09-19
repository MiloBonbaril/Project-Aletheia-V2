# api.py
# FastAPI application for Ollama model interactions
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from ollama_interface.client import OllamaClient

app = FastAPI()

#
# OLLAMA CLIENT INSTANCE
#

client = OllamaClient()

class PullModelRequest(BaseModel):
    model_name: str

class WarmModelRequest(BaseModel):
    model_name: str

class ChatRequest(BaseModel):
    model_name: str
    messages: List[Dict[str, str]]
    options: Optional[Dict[str, Any]] = None

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
        return {"message": response.message.content}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
