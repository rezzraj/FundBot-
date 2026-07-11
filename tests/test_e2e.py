"""
⚠️ LIVE E2E TEST — CONSUMES REAL TOKENS
DO NOT RUN THIS UNLESS EXPLICITLY INSTRUCTED BY THE USER.
Run with: pytest tests/test_e2e_LIVE.py -v
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000/api"

def print_step(step):
    print(f"\n{'-'*50}\n> STEP: {step}\n{'-'*50}")

def run_tests():
    print("Starting End-to-End Smoke Test for Startup Funding API...")
    
    # 1. Test Grants Endpoint
    print_step("Testing GET /grants")
    resp = requests.get(f"{BASE_URL}/grants")
    assert resp.status_code == 200, f"Failed to get grants: {resp.text}"
    grants = resp.json().get("grants", [])
    print(f"Success! Fetched {len(grants)} grants.")

    # 2. Test Profile Creation
    print_step("Testing POST /profiles")
    profile_data = {
        "company_name": "Test AgriTech",
        "stage": "early-stage",
        "location": {"state": "Karnataka"},
        "industries": ["agriculture", "technology"],
        "funding_needed": {"amount": 5000000, "currency": "INR"}
    }
    resp = requests.post(f"{BASE_URL}/profiles", json=profile_data)
    assert resp.status_code == 200, f"Failed to create profile: {resp.text}"
    profile = resp.json()
    profile_id = profile["profile_id"]
    print(f"✅ Created profile with ID: {profile_id}")

    # 3. Test Semantic Search
    print_step("Testing POST /grants/semantic-search")
    search_data = {"query": "agriculture startup looking for early stage funding", "limit": 2}
    resp = requests.post(f"{BASE_URL}/grants/semantic-search", json=search_data)
    assert resp.status_code == 200, f"Failed semantic search: {resp.text}"
    results = resp.json()
    print(f"✅ Semantic search returned {len(results)} results.")

    # 4. Test Chat Session Creation
    print_step("Testing POST /chat/session")
    resp = requests.post(f"{BASE_URL}/chat/session", json={"profile_id": profile_id})
    assert resp.status_code == 200, f"Failed to create chat session: {resp.text}"
    session = resp.json()
    session_id = session["session_id"]
    print(f"✅ Created chat session with ID: {session_id}")

    try:
        # 5. Test Chat Message (AI Tool Calling)
        print_step("Testing POST /chat/message (AI Agent)")
        chat_data = {
            "session_id": session_id,
            "message": "Hi, I have an early-stage agri-tech startup in India and I need seed funding. Can you find some grants for me?"
        }
        print("⏳ Waiting for AI response (this tests Granite LLM + Cloudant tools)...")
        resp = requests.post(f"{BASE_URL}/chat/message", json=chat_data)
        assert resp.status_code == 200, f"Failed chat message: {resp.text}"
        ai_response = resp.json()
        print(f"✅ AI Responded: \n\n{ai_response.get('response', '')}")
        
        print("\n🎉 ALL TESTS PASSED SUCCESSFULLY! The Backend is 100% operational.")

    finally:
        # Cleanup
        print_step("Cleaning Up Junk Data")
        requests.delete(f"{BASE_URL}/profiles/{profile_id}")
        print(f"🧹 Deleted test profile: {profile_id}")

if __name__ == "__main__":
    run_tests()
