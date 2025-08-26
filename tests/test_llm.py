
from voyagerai.backend.llm_interface import LLMWrapper
import os

def test_stub_llm():
    os.environ["LLM_BACKEND"] = "stub"
    llm = LLMWrapper()
    out = llm.chat("hello")
    assert "[STUB]" in out
