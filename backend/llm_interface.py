
import os
import requests

class LLMWrapper:
    def __init__(self):
        self.backend = os.getenv("LLM_BACKEND", "stub").lower()
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.ollama_base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    def chat(self, query: str) -> str:
        if self.backend == "stub":
            return f"[STUB] You asked: {query}\nThis is a simulated response."
        if self.backend == "openai" and self.api_key:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=self.api_key)
                resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": query}],
                    temperature=0.3,
                )
                return resp.choices[0].message.content
            except Exception as e:
                return f"[ERROR] OpenAI call failed: {e}"
        if self.backend == "ollama":
            try:
                r = requests.post(f"{self.ollama_base}/api/generate",
                                 json={"model": "llama3", "prompt": query, "stream": False},
                                 timeout=60)
                r.raise_for_status()
                return r.json().get("response","")
            except Exception as e:
                return f"[ERROR] Ollama call failed: {e}"
        return "[ERROR] Invalid LLM backend or missing API key."
