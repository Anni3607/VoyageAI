import os
import requests
from openai import OpenAI

# This class provides a unified interface for interacting with
# different Large Language Model (LLM) backends.
# It can be configured to use a local stub, OpenAI's API, or a local Ollama server.
class LLMWrapper:
    """
    A wrapper class for interacting with different LLM backends.
    Supports 'stub', 'openai', and 'ollama' backends.
    """
    def __init__(self):
        """
        Initializes the LLMWrapper.
        Reads backend configuration and API keys from environment variables.
        """
        # Determine which LLM backend to use from the environment.
        # Defaults to 'stub' for testing if not specified.
        self.backend = os.getenv("LLM_BACKEND", "stub").lower()
        
        # Get the OpenAI API key from the environment.
        self.api_key = os.getenv("OPENAI_API_KEY")
        
        # Get the base URL for the local Ollama instance.
        # Defaults to the standard local URL.
        self.ollama_base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    def chat(self, query: str) -> str:
        """
        Sends a query to the configured LLM backend and returns the response.

        Args:
            query (str): The text query to send to the LLM.

        Returns:
            str: The response from the LLM, or an error message.
        """
        # --- Stub Backend for Local Testing ---
        if self.backend == "stub":
            return f"[STUB] You asked: {query}\nThis is a simulated response."
        
        # --- OpenAI Backend Integration ---
        if self.backend == "openai" and self.api_key:
            try:
                # Initialize the OpenAI client with the API key.
                client = OpenAI(api_key=self.api_key)
                
                # Create a chat completion request to the specified model.
                resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": query}],
                    temperature=0.3, # A low temperature for more consistent, less creative responses.
                )
                
                # Extract and return the content of the first response choice.
                return resp.choices[0].message.content
            except Exception as e:
                # Catch and report any errors from the OpenAI API call.
                return f"[ERROR] OpenAI call failed: {e}"
        
        # --- Ollama Backend Integration ---
        if self.backend == "ollama":
            try:
                # Prepare the request body for the Ollama generate API.
                payload = {
                    "model": "llama3",
                    "prompt": query,
                    "stream": False # We want the full response at once.
                }
                
                # Make a POST request to the Ollama server.
                r = requests.post(
                    f"{self.ollama_base}/api/generate",
                    json=payload,
                    timeout=60 # Set a timeout for the request.
                )
                
                # Raise an exception for bad status codes (4xx or 5xx).
                r.raise_for_status()
                
                # Return the 'response' field from the JSON payload.
                return r.json().get("response", "")
            except Exception as e:
                # Catch and report any errors from the Ollama API call.
                return f"[ERROR] Ollama call failed: {e}"
        
        # --- Fallback for Invalid Configuration ---
        return "[ERROR] Invalid LLM backend or missing API key."

if __name__ == '__main__':
    # This is an example of how to use the LLMWrapper class.
    # Set the environment variable before running this script:
    # Example: export LLM_BACKEND="openai"
    # Example: export OPENAI_API_KEY="your_key_here"

    wrapper = LLMWrapper()
    
    # Example query.
    user_query = "What is the capital of France?"
    print(f"Querying with backend '{wrapper.backend}': {user_query}")
    
    # Get and print the response.
    response = wrapper.chat(user_query)
    print("--- Response ---")
    print(response)
