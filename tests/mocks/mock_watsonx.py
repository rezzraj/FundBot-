"""
Mock WatsonxService — returns hardcoded responses, ZERO API calls.
Used for ALL development, testing, and debugging.
"""
import json
import random
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"

class MockWatsonxService:
    """Drop-in replacement for WatsonxService that uses zero tokens."""
    
    def __init__(self, **kwargs):
        """Accept and ignore all constructor args to match WatsonxService signature."""
        self._call_count = 0
        self.gemini_client = "mocked"  # Keep this non-None to indicate mocked client is available
    
    def _load_fixture(self, name: str) -> dict:
        path = FIXTURES_DIR / name
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def chat(self, messages, **kwargs) -> dict:
        self._call_count += 1
        user_msg = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                user_msg = m.get("content", "").lower()
                break
        
        if "eligibility" in user_msg or "eligible" in user_msg:
            return self._load_fixture("mock_eligibility_chat_response.json")
        elif "proposal" in user_msg or "draft" in user_msg:
            return self._load_fixture("mock_draft_chat_response.json")
        elif "all" in user_msg or "more" in user_msg:
            return self._load_fixture("mock_list_all_grants_chat_response.json")
        else:
            return self._load_fixture("mock_find_grants_chat_response.json")
    
    def chat_with_tools(self, messages, tools, max_tokens=2000) -> dict:
        self._call_count += 1
        
        # Get the latest user message
        user_msg = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                user_msg = m.get("content", "").lower()
                break

        # Check if this is a follow-up after tool results (return final response)
        has_tool_results = any(m.get("role") == "tool" for m in messages)
        if has_tool_results:
            if "eligibility" in user_msg or "eligible" in user_msg:
                return self._load_fixture("mock_eligibility_chat_response.json")
            elif "proposal" in user_msg or "draft" in user_msg:
                return self._load_fixture("mock_draft_chat_response.json")
            elif "all" in user_msg or "more" in user_msg:
                return self._load_fixture("mock_list_all_grants_chat_response.json")
            else:
                return self._load_fixture("mock_find_grants_chat_response.json")
        
        greetings = {"hi", "hello", "hey", "help"}
        words = set(user_msg.split())
        if greetings.intersection(words) or "what can you do" in user_msg:
            return self._load_fixture("mock_chat_response.json")
        
        # Otherwise return an appropriate tool call
        if "eligibility" in user_msg or "eligible" in user_msg:
            return self._load_fixture("mock_eligibility_tool_call.json")
        elif "proposal" in user_msg or "draft" in user_msg:
            return self._load_fixture("mock_draft_tool_call.json")
        elif "all" in user_msg or "more" in user_msg:
            return self._load_fixture("mock_list_all_grants_tool_call.json")
        else:
            return self._load_fixture("mock_tool_call_response.json")
    
    def get_response_text(self, response) -> str:
        try:
            return response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            return str(response)
    
    def embed_texts(self, texts) -> list:
        """Return random 768-dim vectors — no API call."""
        return [[random.random() for _ in range(768)] for _ in texts]
    
    def embed_query(self, query) -> list:
        """Return random 768-dim vector — no API call."""
        return [random.random() for _ in range(768)]
    
    def check_eligibility(self, grant, profile) -> dict:
        self._call_count += 1
        return self._load_fixture("mock_eligibility_response.json")
    
    def explain_grant(self, grant) -> str:
        self._call_count += 1
        data = self._load_fixture("mock_explain_response.json")
        return data["explanation"]
    
    def get_chat_model(self):
        return None
    
    def get_embeddings_model(self):
        return None
