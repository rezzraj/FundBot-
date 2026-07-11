import json
from typing import Any

from apps.api.services.watsonx_service import WatsonxService
from apps.api.services.embedding_service import EmbeddingService
from shared.prompts.drafting_prompts import PROPOSAL_DRAFT_PROMPT


class DraftingService:
    """
    Generates tailored grant proposal drafts using Granite + RAG.
    Retrieves similar grant descriptions for context enrichment.
    """

    def __init__(self, watsonx: WatsonxService, embedding: EmbeddingService):
        self.watsonx = watsonx
        self.embedding = embedding

    def _build_context(self, grant: dict, profile: dict) -> str:
        """Build rich context for the proposal generation prompt."""
        context_parts = []

        # Grant details
        context_parts.append("=== GRANT DETAILS ===")
        context_parts.append(f"Name: {grant.get('grant_name', '')}")
        context_parts.append(f"Provider: {grant.get('provider', {}).get('name', '')}")
        context_parts.append(f"Description: {grant.get('description', '')}")

        funding = grant.get("funding", {})
        if funding.get("maximum_amount"):
            context_parts.append(
                f"Maximum Funding: {funding.get('currency', 'INR')} {funding['maximum_amount']}"
            )
        context_parts.append(f"Type: {funding.get('funding_type', '')}")

        eligibility = grant.get("eligibility", {})
        if eligibility.get("company_requirements"):
            context_parts.append(
                f"Requirements: {json.dumps(eligibility['company_requirements'])}"
            )

        application = grant.get("application", {})
        if application.get("required_documents"):
            context_parts.append(
                f"Required Documents: {json.dumps(application['required_documents'])}"
            )

        # Startup profile
        context_parts.append("\n=== STARTUP PROFILE ===")
        context_parts.append(f"Company: {profile.get('company_name', '')}")
        context_parts.append(f"Stage: {profile.get('stage', '')}")
        context_parts.append(f"Industries: {', '.join(profile.get('industries', []))}")
        context_parts.append(f"Description: {profile.get('description', '')}")
        context_parts.append(f"Team Size: {profile.get('team_size', 'Unknown')}")
        context_parts.append(f"Location: {json.dumps(profile.get('location', {}))}")

        funding_needed = profile.get("funding_needed", {})
        if funding_needed.get("amount"):
            context_parts.append(
                f"Funding Needed: {funding_needed.get('currency', 'INR')} {funding_needed['amount']}"
            )

        return "\n".join(context_parts)

    async def generate_draft(
        self,
        grant: dict,
        profile: dict,
        additional_context: str | None = None,
    ) -> dict:
        """
        Generate a complete proposal draft with all sections.
        Returns a dict with section keys and content values.
        """
        context = self._build_context(grant, profile)

        # RAG: Retrieve similar grants for additional context
        query = f"{grant.get('grant_name', '')} {grant.get('description', '')}"
        similar_grants_response = self.embedding.search_similar_grants(query=query, limit=3)

        if similar_grants_response and similar_grants_response.get("documents") and similar_grants_response["documents"][0]:
            context += "\n\n=== SIMILAR GRANTS (for reference) ===\n"
            for doc in similar_grants_response["documents"][0]:
                context += f"- {doc}\n"

        if additional_context:
            context += f"\n\n=== ADDITIONAL CONTEXT ===\n{additional_context}"

        messages = [
            {"role": "system", "content": PROPOSAL_DRAFT_PROMPT},
            {"role": "user", "content": context},
        ]

        response = self.watsonx.chat(
            messages=messages,
            params={"max_tokens": 4000, "temperature": 0.4},
        )

        content = self.watsonx.get_response_text(response)

        # Parse the JSON response
        try:
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            draft = json.loads(content.strip())
        except json.JSONDecodeError:
            # If Granite doesn't output clean JSON, wrap the raw text
            draft = {
                "executive_summary": content,
                "raw_output": True,
            }

        return {
            "grant_id": grant.get("_id"),
            "grant_name": grant.get("grant_name"),
            "profile_id": profile.get("_id"),
            "draft_content": draft,
            "model_used": "ibm/granite-4-h-small",
            "requires_human_review": True,
        }

    async def refine_section(
        self,
        section_name: str,
        current_content: str,
        feedback: str,
        grant: dict,
        profile: dict,
    ) -> str:
        """Refine a specific section based on founder feedback."""
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a grant proposal editor. Refine the given section based on "
                    "the founder's feedback. Maintain professional tone and factual accuracy. "
                    "Output ONLY the revised section text."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Section: {section_name}\n\n"
                    f"Current content:\n{current_content}\n\n"
                    f"Founder's feedback:\n{feedback}\n\n"
                    f"Grant: {grant.get('grant_name', '')}\n"
                    f"Startup: {profile.get('company_name', '')}"
                ),
            },
        ]

        response = self.watsonx.chat(messages=messages, params={"max_tokens": 1500, "temperature": 0.3})
        return self.watsonx.get_response_text(response)
