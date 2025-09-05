# client.py
# Interface for interacting with Ollama models
import ollama
from typing import List, Optional, Dict, Any

class OllamaClient:
    def __init__(self, api_url: str = "http://localhost:11434"):
        self.client = ollama.Client(host=api_url)

    def list_models(self) -> List[Dict[str, Any]]:
        """List available models."""
        return self.client.list()

    def pull_model(self, model_name: str) -> None:
        """Pull a model from the Ollama repository."""
        self.client.pull(model_name)

    def warm_model(self, model_name: str) -> None:
        """Warm up a model to reduce initial latency."""
        result = self.client.generate(model_name, "Hello", think=False)
        return result

    def chat(self, model_name: str, messages: List[Dict[str, str]], options: Optional[Dict[str, Any]] = None) -> ollama.ChatResponse:
        """Generate a chat response from the model."""
        return self.client.chat(model_name, messages, options=options or {})

if __name__ == "__main__":
    client = OllamaClient()
    #print("Available models:", client.list_models())
    model_name = "qwen3:1.7b"
    #client.pull_model(model_name)
    #print("DEBUG:",client.warm_model(model_name))
    response = client.chat(model_name, [{"role": "user", "content": "Hello, how are you?"}])
    print("Response:", response.message.content)