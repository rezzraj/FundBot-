import json
from typing import Any, Dict, Optional
from apps.api.services.watsonx_service import WatsonxService
from shared.prompts.extraction_prompts import GRANT_EXTRACTION_PROMPT

class ExtractionService:
    def __init__(self, watsonx_service: WatsonxService):
        self.watsonx = watsonx_service

    async def extract_grant_from_text(self, text: str, source_url: str, source_type: str) -> Optional[Dict[str, Any]]:
        prompt = GRANT_EXTRACTION_PROMPT.format(text=text, source_url=source_url, source_type=source_type)
        messages = [{"role": "user", "content": prompt}]
        
        response = self.watsonx.chat(messages, model_type="chat")
        content = self.watsonx.get_response_text(response)
        
        try:
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
                
            return json.loads(content.strip())
        except Exception as e:
            print(f"Extraction failed to parse JSON: {e}")
            return None
