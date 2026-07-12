import asyncio
import json
from dotenv import load_dotenv; load_dotenv()
from apps.api.config import get_settings
from apps.api.services.cloudant_service import CloudantService
from apps.api.services.agent_service import AgentService
from tests.mocks.mock_watsonx import MockWatsonxService

class MockMatchingService:
    async def match_profile_to_grants(self, profile, top_n=5):
        print("\n--- MATCHING SERVICE RECEIVED PROFILE ---")
        print(json.dumps(profile, indent=2))
        print("-----------------------------------------")
        if profile.get("description"):
            print("SUCCESS: Description is present in the profile!")
        else:
            print("FAILURE: Description is missing!")
        
        class MockMatch:
            def __init__(self):
                self.grant_name = "Test Grant"
                self.grant_id = "test-grant"
                self.final_score = 0.95
                self.eligible = True
                self.explanation = "Perfect match"
        return [MockMatch()]

async def verify():
    settings = get_settings()
    cloudant = CloudantService(settings.cloudant_api_key, settings.cloudant_url, settings.cloudant_database)
    watsonx = MockWatsonxService()
    matching = MockMatchingService()
    agent = AgentService(watsonx=watsonx, cloudant=cloudant, matching=matching, drafting=None, embedding=None)
    
    profile_data = {
        "type": "startup_profile",
        "company_name": "New BioTech",
        "stage": "early-stage",
        "industries": ["biotechnology"],
        "location": {"country": "India"},
        "description": "We build highly advanced biotech reactors and medical devices.",
        "funding_needed": {"amount": 500000, "types": ["grant"], "currency": "INR"}
    }
    profile_doc = cloudant.create_profile(profile_data)
    profile_id = profile_doc["id"]
    
    arguments = {"top_n": 5}
    
    print("Executing match_profile through AgentService...")
    result_json = await agent._execute_tool("match_profile", arguments, profile_id=profile_id)
    print("\nResults:")
    print(result_json)

if __name__ == "__main__":
    asyncio.run(verify())
