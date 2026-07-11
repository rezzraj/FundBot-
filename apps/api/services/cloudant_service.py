import os
import uuid
from datetime import datetime, timezone
from typing import Any

from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from ibmcloudant.cloudant_v1 import CloudantV1, Document


class CloudantService:
    """Wrapper around IBM Cloudant for all database operations."""

    def __init__(self, api_key: str, url: str, database: str):
        authenticator = IAMAuthenticator(api_key)
        self.client = CloudantV1(authenticator=authenticator)
        self.client.set_service_url(url)
        self.db = database

    # ----- Generic Operations -----

    def get_document(self, doc_id: str) -> dict | None:
        try:
            return self.client.get_document(db=self.db, doc_id=doc_id).get_result()
        except Exception:
            return None

    def create_document(self, doc: dict) -> dict:
        if "_id" not in doc:
            doc["_id"] = str(uuid.uuid4())
        doc["created_at"] = datetime.now(timezone.utc).isoformat()
        doc["updated_at"] = doc["created_at"]
        return self.client.post_document(db=self.db, document=doc).get_result()

    def update_document(self, doc: dict) -> dict:
        doc["updated_at"] = datetime.now(timezone.utc).isoformat()
        return self.client.post_document(db=self.db, document=doc).get_result()

    def delete_document(self, doc_id: str, rev: str) -> dict:
        return self.client.delete_document(db=self.db, doc_id=doc_id, rev=rev).get_result()

    # ----- Grant Queries -----

    def find_grants(self, selector: dict, limit: int = 50) -> list[dict]:
        result = self.client.post_find(
            db=self.db,
            selector={"type": {"$in": ["grant", "funding_opportunity"]}, **selector},
            limit=limit,
        ).get_result()
        return result.get("docs", [])

    def get_all_active_grants(self, limit: int = 200) -> list[dict]:
        return self.find_grants(
            selector={"status": {"$in": ["active", "upcoming", "unknown"]}},
            limit=limit,
        )

    def search_grants_by_fields(
        self,
        stage: str | None = None,
        industries: list[str] | None = None,
        location: str | None = None,
        funding_type: str | None = None,
        limit: int = 20,
    ) -> list[dict]:
        """Build a Cloudant Mango query from search parameters."""
        selector: dict[str, Any] = {
            "type": {"$in": ["grant", "funding_opportunity"]},
            "status": {"$in": ["active", "upcoming", "unknown"]},
        }
        # Stage and location matching is done in-memory (like agent_tools.py)
        # because Cloudant doesn't support array-contains well on Lite
        grants = self.find_grants(selector=selector, limit=200)
        return grants  # Filter in-memory using matching_service

    # ----- Profile Operations -----

    def get_profile(self, profile_id: str) -> dict | None:
        return self.get_document(profile_id)

    def create_profile(self, profile_data: dict) -> dict:
        profile_data["_id"] = f"profile-{uuid.uuid4()}"
        profile_data["type"] = "startup_profile"
        return self.create_document(profile_data)

    def update_profile(self, profile_data: dict) -> dict:
        return self.update_document(profile_data)

    # ----- Application Operations -----

    def create_application(self, app_data: dict) -> dict:
        app_data["_id"] = f"app-{uuid.uuid4()}"
        app_data["type"] = "application"
        app_data["status"] = "draft"
        return self.create_document(app_data)

    def get_applications_for_profile(self, profile_id: str) -> list[dict]:
        return self.find_grants(
            selector={"type": "application", "profile_id": profile_id}
        )

    # ----- Chat Session Operations -----

    def create_chat_session(self, profile_id: str) -> dict:
        return self.create_document({
            "_id": f"chat-{uuid.uuid4()}",
            "type": "chat_session",
            "profile_id": profile_id,
            "messages": [],
        })

    def append_message(self, session_id: str, message: dict) -> dict:
        session = self.get_document(session_id)
        if not session:
            raise ValueError(f"Chat session {session_id} not found")
        session["messages"].append({
            **message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return self.update_document(session)
