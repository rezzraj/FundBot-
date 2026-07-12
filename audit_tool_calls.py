import json
from dotenv import load_dotenv; load_dotenv()
from apps.api.config import get_settings; from apps.api.services.cloudant_service import CloudantService

s=get_settings()
c=CloudantService(s.cloudant_api_key, s.cloudant_url, s.cloudant_database)
# Find chat sessions
sessions = c.client.post_find(
    db=c.db,
    selector={"type": "chat_session"},
    limit=50
).get_result().get("docs", [])

found = False
for sess in sessions:
    for msg in sess.get("messages", []):
        if msg.get("role") == "assistant" and "tool_calls" in msg:
            for tc in msg["tool_calls"]:
                if tc["function"]["name"] == "match_profile":
                    args = json.loads(tc["function"]["arguments"])
                    print(f"Session {sess['_id']} match_profile args:")
                    print(json.dumps(args, indent=2))
                    found = True
if not found:
    print("No recent match_profile tool calls found in database.")
