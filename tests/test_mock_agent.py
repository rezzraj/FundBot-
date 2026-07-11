"""
Unit and integration tests for mock Agent & SSE Streaming.
Guarantees ZERO tokens are used.
"""
import json
import pytest
from fastapi.testclient import TestClient

def test_health_check(client: TestClient):
    """Test that the API health check works."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "grant-finder-api"}

def test_startup_profile_crud(client: TestClient, sample_profile):
    """Test startup profile creation and loading."""
    # Create profile
    response = client.post("/api/profiles", json=sample_profile)
    assert response.status_code == 200
    data = response.json()
    assert "profile_id" in data
    
    profile_id = data["profile_id"]
    
    # Load profile
    get_response = client.get(f"/api/profiles/{profile_id}")
    assert get_response.status_code == 200
    profile_data = get_response.json()
    assert profile_data["company_name"] == "TestAgriTech"
    assert profile_data["stage"] == "early-stage"

def test_chat_session_creation(client: TestClient, sample_profile):
    """Test creating a chat session linked to a profile."""
    # Create profile
    prof_resp = client.post("/api/profiles", json=sample_profile)
    profile_id = prof_resp.json()["profile_id"]
    
    # Create chat session
    session_resp = client.post("/api/chat/session", json={"profile_id": profile_id})
    assert session_resp.status_code == 200
    sess_data = session_resp.json()
    assert "session_id" in sess_data
    assert sess_data["status"] == "created"

def test_agent_message_find_grants(client: TestClient, sample_profile):
    """Test finding matching grants (tabular response)."""
    # Setup profile and session
    p_id = client.post("/api/profiles", json=sample_profile).json()["profile_id"]
    s_id = client.post("/api/chat/session", json={"profile_id": p_id}).json()["session_id"]
    
    # Send search message
    response = client.post(
        "/api/chat/message",
        json={"session_id": s_id, "message": "find me matching grants"}
    )
    assert response.status_code == 200
    res_data = response.json()
    assert "response" in res_data
    assert "Startup India Seed Fund Scheme" in res_data["response"]
    assert "| Grant Name | Provider |" in res_data["response"]  # Verification of Markdown table!

def test_agent_message_eligibility(client: TestClient, sample_profile):
    """Test eligibility query response."""
    p_id = client.post("/api/profiles", json=sample_profile).json()["profile_id"]
    s_id = client.post("/api/chat/session", json={"profile_id": p_id}).json()["session_id"]
    
    response = client.post(
        "/api/chat/message",
        json={"session_id": s_id, "message": "check my eligibility for SISFS"}
    )
    assert response.status_code == 200
    res_data = response.json()
    assert "response" in res_data
    assert "Eligibility Checklist" in res_data["response"]
    assert "✅" in res_data["response"]

def test_sse_streaming_endpoint(client: TestClient, sample_profile):
    """Test that SSE message stream returns valid chunked tool events."""
    p_id = client.post("/api/profiles", json=sample_profile).json()["profile_id"]
    s_id = client.post("/api/chat/session", json={"profile_id": p_id}).json()["session_id"]
    
    # Request SSE stream
    with client.stream(
        "POST",
        "/api/chat/message/stream",
        json={"session_id": s_id, "message": "find me matching grants"}
    ) as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        
        events = []
        for line in response.iter_lines():
            if line.startswith("data: "):
                event_content = line[6:]
                if event_content == "[DONE]":
                    break
                events.append(json.loads(event_content))
        
        # Verify that we received progress/tool events and final response event
        assert len(events) >= 3
        
        # Verify events contain thinking/tool_start/tool_complete/ai_processing/response
        types = [e["type"] for e in events]
        assert "thinking" in types
        assert "tool_start" in types or "tool_complete" in types or "response" in types
        
        # Verify that the final response contains tabular grants data
        final_resp = next(e for e in events if e["type"] == "response")
        assert "| Grant Name | Provider |" in final_resp["content"]
