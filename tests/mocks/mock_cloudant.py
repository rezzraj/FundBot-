"""
Mock CloudantService — in-memory dict store, ZERO Cloudant API calls.
"""
import uuid
import json
from datetime import datetime, timezone
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"

class MockCloudantService:
    def __init__(self, **kwargs):
        self._store = {}
        self._load_grants()
    
    def _load_grants(self):
        path = FIXTURES_DIR / "mock_grants.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            grants = data if isinstance(data, list) else data.get("docs", data.get("grants", []))
            for g in grants:
                self._store[g["_id"]] = g
    
    def get_document(self, doc_id):
        return self._store.get(doc_id)
    
    def create_document(self, doc):
        if "_id" not in doc:
            doc["_id"] = str(uuid.uuid4())
        doc["created_at"] = datetime.now(timezone.utc).isoformat()
        doc["updated_at"] = doc["created_at"]
        self._store[doc["_id"]] = doc
        return {"ok": True, "id": doc["_id"], "rev": "1-mock"}
    
    def update_document(self, doc):
        doc["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._store[doc["_id"]] = doc
        return {"ok": True, "id": doc["_id"], "rev": "2-mock"}
    
    def delete_document(self, doc_id, rev=None):
        self._store.pop(doc_id, None)
        return {"ok": True}
    
    def find_grants(self, selector=None, limit=50):
        # Very simple mango-like selector filter in memory
        grants = [
            v for v in self._store.values()
            if v.get("type") in ("grant", "funding_opportunity")
        ]
        if selector:
            # Simple match checking
            filtered = []
            for g in grants:
                matches = True
                for k, val in selector.items():
                    if k == "_id" and g.get("_id") != val:
                        matches = False
                        break
                if matches:
                    filtered.append(g)
            grants = filtered
        return grants[:limit]
    
    def get_all_active_grants(self, limit=200):
        return [
            v for v in self._store.values()
            if v.get("type") in ("grant", "funding_opportunity")
            and v.get("status") in ("active", "upcoming", "unknown")
        ][:limit]
    
    def search_grants_by_fields(self, **kwargs):
        return self.get_all_active_grants()
    
    def get_profile(self, profile_id):
        return self.get_document(profile_id)
    
    def create_profile(self, profile_data):
        profile_data["_id"] = f"profile-{uuid.uuid4()}"
        profile_data["type"] = "startup_profile"
        return self.create_document(profile_data)
    
    def update_profile(self, profile_data):
        return self.update_document(profile_data)
    
    def create_application(self, app_data):
        app_data["_id"] = f"app-{uuid.uuid4()}"
        app_data["type"] = "application"
        app_data["status"] = "draft"
        return self.create_document(app_data)
    
    def get_applications_for_profile(self, profile_id):
        return [
            v for v in self._store.values()
            if v.get("type") == "application" and v.get("profile_id") == profile_id
        ]
    
    def create_chat_session(self, profile_id):
        return self.create_document({
            "_id": f"chat-{uuid.uuid4()}",
            "type": "chat_session",
            "profile_id": profile_id,
            "messages": [],
        })
    
    def append_message(self, session_id, message):
        session = self._store.get(session_id)
        if not session:
            raise ValueError(f"Chat session {session_id} not found")
        session["messages"].append({
            **message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        self._store[session_id] = session
        return {"ok": True}
