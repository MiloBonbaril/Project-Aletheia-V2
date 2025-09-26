# client.py
# Interface for interacting with Ollama models
from groq import Groq
import os
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv

class GroqClient:
    def __init__(self, api_key: str = os.getenv('GROQ_API_KEY'), ):
        self.client: Groq = Groq(
            api_key=api_key,
            max_retries=2,
            default_headers={
            "Groq-Model-Version": "latest"
            }
        )

    def list_models(self) -> List[Dict[str, Any]]:
        """List available models."""
        return Groq.models

    def pull_model(self, model_name: str) -> None:
        """Pull a model from the Ollama repository."""
        return {"error": "Can't pull model on Groq"}

    def warm_model(self, model_name: str) -> None:
        """Warm up a model to reduce initial latency."""
        return {"error": "No need to warm model on Groq"}

    def chat(self, model_name: str, messages: List[Dict[str, str]], options: Optional[Dict[str, Any]] = None):
        """Generate a chat response from the model."""
        seed = 42
        if options:
            if 'seed' in options.keys():
                try:
                    seed = int(options['seed'])
                except Exception as e:
                    pass
        return self.client.chat.completions.create(messages=messages, model=model_name, seed=seed, stream=False)

if __name__ == "__main__":
    load_dotenv(".env")
    client = GroqClient()
    #print("Available models:", client.list_models())
    model_name = "meta-llama/llama-4-scout-17b-16e-instruct"
    #client.pull_model(model_name)
    #print("DEBUG:",client.warm_model(model_name))
    response = client.chat(model_name, [{"role": "user", "content": "Hello, how are you?"}])
    print("Response:", response)