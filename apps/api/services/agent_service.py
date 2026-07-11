import json
from typing import Any
import asyncio
import time
from datetime import datetime, timezone

from apps.api.services.watsonx_service import WatsonxService
from apps.api.services.cloudant_service import CloudantService
from apps.api.services.matching_service import MatchingService
from apps.api.services.drafting_service import DraftingService
from apps.api.services.embedding_service import EmbeddingService


# ==========================================
# TOOL SCHEMAS
# ==========================================

TOOLS = [
    # Tool 1: Search grants
    {
        "type": "function",
        "function": {
            "name": "search_grants",
            "description": (
                "ONLY use when the user manually provides filters. "
                "Do NOT use if a profile already exists. "
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "startup_stage": {
                        "type": "string",
                        "enum": ["idea", "prototype", "early-stage", "growth-stage", "scaling", "unknown"],
                        "description": "Current stage of the startup.",
                    },
                    "industries": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Industries the startup operates in.",
                    },
                    "location": {
                        "type": "string",
                        "description": "Country or region where the startup is registered.",
                    },
                    "funding_types": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["grant", "seed_funding", "equity_investment", "loan", "subsidy", "prize", "financial_assistance"],
                        },
                        "description": "Preferred funding types.",
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 20,
                        "default": 5,
                        "description": "Maximum grants to return.",
                    },
                },
                "required": ["startup_stage", "industries", "location"],
            },
        },
    },

    # Tool 2: Get grant details
    {
        "type": "function",
        "function": {
            "name": "get_grant_detail",
            "description": "Get full details of a specific grant by its ID. Use when the user asks about a specific grant.",
            "parameters": {
                "type": "object",
                "properties": {
                    "grant_id": {
                        "type": "string",
                        "description": "The unique ID of the grant (e.g., 'startup-india-seed-fund-scheme').",
                    },
                },
                "required": ["grant_id"],
            },
        },
    },

    # Tool 3: Match profile to grants
    {
        "type": "function",
        "function": {
            "name": "match_profile",
            "description": (
                "ONLY use when a startup profile already exists. "
                "Read information from the profile. "
                "Return personalized recommendations."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "company_name": {"type": "string", "description": "Name of the startup."},
                    "stage": {
                        "type": "string",
                        "enum": ["idea", "prototype", "early-stage", "growth-stage", "scaling"],
                        "description": "Current startup stage.",
                    },
                    "industries": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Industries the startup operates in.",
                    },
                    "location": {"type": "string", "description": "Startup's location (city, state, or country)."},
                    "description": {"type": "string", "description": "Brief description of what the startup does."},
                    "funding_amount": {"type": "number", "description": "Amount of funding needed."},
                    "funding_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Preferred funding types.",
                    },
                    "top_n": {"type": "integer", "default": 5, "description": "Number of matches to return."},
                },
                "required": ["stage", "industries", "location"],
            },
        },
    },

    # Tool 4: Check eligibility
    {
        "type": "function",
        "function": {
            "name": "check_eligibility",
            "description": "Check if a specific startup is eligible for a specific grant. Provides detailed eligibility analysis.",
            "parameters": {
                "type": "object",
                "properties": {
                    "grant_id": {"type": "string", "description": "The grant ID to check."},
                    "profile_id": {"type": "string", "description": "The startup profile ID. Optional if profile details are provided inline."},
                },
                "required": ["grant_id"],
            },
        },
    },

    # Tool 5: Draft proposal
    {
        "type": "function",
        "function": {
            "name": "draft_proposal",
            "description": (
                "Generate a tailored grant application proposal for a startup. "
                "Use when the user asks to help write or draft an application."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "grant_id": {"type": "string", "description": "The grant to apply for."},
                    "profile_id": {"type": "string", "description": "The startup profile ID."},
                    "additional_context": {
                        "type": "string",
                        "description": "Any additional information the founder wants to include.",
                    },
                },
                "required": ["grant_id"],
            },
        },
    },

    # Tool 6: Explain grant
    {
        "type": "function",
        "function": {
            "name": "explain_grant",
            "description": "Provide a clear, founder-friendly explanation of a grant opportunity.",
            "parameters": {
                "type": "object",
                "properties": {
                    "grant_id": {"type": "string", "description": "The grant to explain."},
                },
                "required": ["grant_id"],
            },
        },
    },

    # Tool 7: Semantic search
    {
        "type": "function",
        "function": {
            "name": "semantic_search",
            "description": (
                "Search for grants using natural language. Use when the user describes "
                "what they're looking for in conversational language rather than structured filters."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language search query.",
                    },
                    "limit": {
                        "type": "integer",
                        "default": 5,
                        "description": "Number of results.",
                    },
                },
                "required": ["query"],
            },
        },
    },
]


# ==========================================
# AGENT SYSTEM PROMPT
# ==========================================

AGENT_SYSTEM_PROMPT = """You are FundBot, an AI assistant specialized in helping Indian startups find grants and funding opportunities.

You have access to a database of curated startup grants from government programs (Startup India, BIRAC, iDEX, KSUM, Startup Odisha, etc.) and other funding sources.

Your capabilities:
1. **Search grants** by stage, industry, location, and funding type
2. **Semantic search** using natural language descriptions
3. **Match** a startup's profile against available grants
4. **Check eligibility** for specific grants
5. **Explain grants** in clear, founder-friendly language
6. **Draft proposals** tailored to specific grant applications

Guidelines:
- Always be helpful, specific, and actionable. Use a friendly, consultative tone.
- Recommend grants proactively based on the conversation context.
- When explaining grants, highlight deadlines and key requirements.
- **CRITICAL FORMATTING RULE**: NEVER output raw JSON, lists of "Met Criteria", or "Unmet Criteria". NEVER use robotic formats. Always synthesize tool outputs into natural, conversational paragraphs. For example, instead of "Met Criteria: Industry matches 'technology'", say "This grant is a great fit because it specifically targets technology startups."
- **TABLE FORMATTING RULE**: When listing multiple grants from a search or match, ALWAYS list the top 5 grants FIRST in a Markdown table. Do not provide a long detailed list of every grant unless the user explicitly asks for it (e.g., "list all" or "show more"). Simply mention that more are available.
- **STRICT NO-LOOP RULE**: You must NEVER call the same tool multiple times in a row. If you perform any search (`semantic_search`, `search_grants`, `match_profile`), the output contains all the information you need. You MUST immediately reply to the user. **DO NOT iteratively call explain_grant or check_eligibility on the results.** If the user asked you to draft a proposal, perform ONE search to find the correct grant ID, then immediately call `draft_proposal` with that exact ID. NEVER call `explain_grant` when drafting a proposal.
- **STRICT NO-ASKING RULE**: If a startup profile already exists in the system prompt, you MUST NEVER ask the user again for: startup description, industry, startup stage, location, or funding amount. Use the profile exactly as provided. If the user asks: "find matching grants", "find grants", "recommend grants", "search grants", or "funding opportunities", you MUST immediately call `match_profile`. Never respond with follow-up questions unless absolutely required. If description is empty, pass `description=""` instead of asking.
- **GENERAL CHAT RULE**: If the user asks a general question (e.g., "what can you do?", "hi", "how does this work?"), **DO NOT use any tools**. Just reply directly with a helpful, conversational answer based on your capabilities.
- When drafting proposals, format them cleanly using Markdown. Always note that they need human review.
- If you're unsure about eligibility, say so — never give false confidence.
- Use INR amounts for Indian grants.

IMPORTANT: You must ALWAYS use your tools to provide accurate, data-backed responses. Do NOT make up grant information. If a tool returns no results, honestly tell the user.

SAFETY RULES (always follow):
- Never fabricate grant information. Only reference data from your tools.
- Never promise or guarantee grant approval or funding outcomes.
- Never expose personal information (PII) in responses.
- Always note that AI-generated content requires human review.
- Use factual language; avoid superlatives or misleading claims.
"""


# ==========================================
# AGENT ORCHESTRATION
# ==========================================

class AgentService:
    """
    Conversational AI agent that orchestrates all tools.
    Uses Granite's native tool-calling capability.
    """

    def __init__(
        self,
        watsonx: WatsonxService,
        cloudant: CloudantService,
        matching: MatchingService,
        drafting: DraftingService,
        embedding: EmbeddingService,
    ):
        self.watsonx = watsonx
        self.cloudant = cloudant
        self.matching = matching
        self.drafting = drafting
        self.embedding = embedding

    async def _execute_tool(self, tool_name: str, arguments: dict, profile_id: str | None = None) -> str:
        """Route tool calls to the appropriate service."""
        try:
            if tool_name == "search_grants":
                from agent_tools import search_grants
                from data.structured.data_validation import SearchGrantsInput
                if isinstance(arguments.get("industries"), str):
                    arguments["industries"] = [arguments["industries"]]
                if isinstance(arguments.get("funding_types"), str):
                    arguments["funding_types"] = [arguments["funding_types"]]
                search_input = SearchGrantsInput(**arguments)
                result = search_grants(search_input)
                return json.dumps(result, indent=2, default=str)
                
            elif tool_name == "get_grant_detail":
                grant = self.cloudant.get_document(arguments["grant_id"])
                if grant:
                    return json.dumps(grant, indent=2, default=str)
                return json.dumps({"error": f"Grant '{arguments['grant_id']}' not found"})
                
            elif tool_name == "match_profile":
                profile = {
                    "stage": arguments.get("stage"),
                    "industries": arguments.get("industries", []),
                    "location": {"country": arguments.get("location", "India")},
                    "company_name": arguments.get("company_name", ""),
                    "description": arguments.get("description", ""),
                    "funding_needed": {
                        "amount": arguments.get("funding_amount"),
                        "types": arguments.get("funding_types", []),
                        "currency": "INR",
                    },
                }
                matches = await self.matching.match_profile_to_grants(
                    profile, top_n=arguments.get("top_n", 5),
                )
                return json.dumps([
                    {
                        "grant_name": m.grant_name,
                        "grant_id": m.grant_id,
                        "match_score": m.final_score,
                        "eligibility_status": m.eligible,
                        "why_it_matches": m.explanation,
                    }
                    for m in matches if str(m.eligible) != "False" and not str(m.eligible).startswith("Not eligible") and m.final_score > 0
                ], indent=2)

            elif tool_name == "check_eligibility":
                grant = self.cloudant.get_document(arguments["grant_id"])
                if not grant:
                    return json.dumps({"error": "Grant not found. STOP calling tools and ask the user to clarify which grant they are referring to."})

                profile = {}
                # Automatically inject profile_id if not provided
                if "profile_id" not in arguments and profile_id:
                    arguments["profile_id"] = profile_id
                    
                if "profile_id" in arguments:
                    profile = self.cloudant.get_document(arguments["profile_id"]) or {}

                result = self.watsonx.check_eligibility(grant, profile)
                return json.dumps(result, indent=2, default=str)

            elif tool_name == "draft_proposal":
                grant = self.cloudant.get_document(arguments["grant_id"])
                if not grant:
                    return json.dumps({"error": "Grant not found. STOP calling tools and ask the user to specify which grant they want to apply for."})

                profile = {}
                # Automatically inject profile_id if not provided
                if "profile_id" not in arguments and profile_id:
                    arguments["profile_id"] = profile_id
                    
                if "profile_id" in arguments:
                    profile = self.cloudant.get_document(arguments["profile_id"]) or {}

                draft = await self.drafting.generate_draft(
                    grant, profile, arguments.get("additional_context"),
                )
                return json.dumps(draft, indent=2, default=str)

            elif tool_name == "explain_grant":
                grant = self.cloudant.get_document(arguments["grant_id"])
                if not grant:
                    return json.dumps({"error": "Grant not found. STOP calling tools and ask the user to clarify."})

                explanation = self.watsonx.explain_grant(grant)
                return json.dumps({"explanation": explanation})

            elif tool_name == "semantic_search":
                results = self.embedding.semantic_search_grants(
                    query=arguments["query"],
                    n_results=arguments.get("limit", 5),
                )
                return json.dumps(results, indent=2, default=str)

            return json.dumps({"error": f"Unknown tool: {tool_name}"})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return json.dumps({"error": f"Error executing tool {tool_name}: {str(e)}"})

    async def process_message(
        self,
        session_id: str,
        user_message: str,
        on_event: callable = None,
    ) -> str:
        """
        Process a user message through the agent loop.
        Handles multi-turn tool calling automatically.
        """
        # Load conversation history
        session = self.cloudant.get_document(session_id)
        if not session:
            # Auto-create the session for testing convenience
            session = {
                "_id": session_id,
                "type": "chat_session",
                "profile_id": "test_profile",
                "messages": []
            }
            self.cloudant.create_document(session)

        # Inject Profile Context dynamically
        profile_id = session.get("profile_id")
        profile = self.cloudant.get_profile(profile_id)
        
        system_prompt = AGENT_SYSTEM_PROMPT
        if profile:
            profile_context = (
                f"\n\n=== STARTUP PROFILE ===\n"
                f"Company:\n{profile.get('company_name', 'Unknown')}\n\n"
                f"Stage:\n{profile.get('stage', 'Unknown')}\n\n"
                f"Industries:\n{', '.join(profile.get('industries', []))}\n\n"
                f"Location:\n{profile.get('location', {}).get('country', 'Unknown')}\n\n"
                f"Description:\n{profile.get('description', '')}\n\n"
                f"Funding Needed:\n{profile.get('funding_needed', {}).get('amount', 'Unknown')} INR\n"
                f"=== END PROFILE ===\n\n"
                f"This profile is authoritative. Use it for every recommendation. Do not ask the user for any of these values."
            )
            system_prompt += profile_context

        # Build messages list
        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history (last 20 messages for context window)
        for msg in session.get("messages", [])[-20:]:
            messages.append({
                "role": msg["role"],
                "content": msg["content"],
            })

        # Add new user message
        messages.append({"role": "user", "content": user_message})

        # Save user message
        self.cloudant.append_message(session_id, {"role": "user", "content": user_message})

        # Agent loop: handle multiple tool calls
        max_iterations = 10
        for _ in range(max_iterations):
            if on_event:
                await self._emit(on_event, {"type": "thinking", "content": "Analyzing your request..."})

            try:
                print(f"Loaded profile:\n{json.dumps(profile, indent=2) if profile else 'None'}")
                print("Calling Gemini...")
                response = self.watsonx.chat_with_tools(
                    messages=messages,
                    tools=TOOLS,
                    max_tokens=3000,
                )
            except Exception as e:
                import traceback
                traceback.print_exc()
                error_msg = f"Sorry, my AI models are currently exhausted or unavailable due to API rate limits. Please try again later. (Error: {str(e)})"
                self.cloudant.append_message(session_id, {"role": "assistant", "content": error_msg})
                if on_event:
                    await self._emit(on_event, {"type": "error", "content": error_msg})
                return error_msg

            assistant_message = response["choices"][0]["message"]
            print("\n========================")
            print("Assistant Message")
            print("========================")
            print(json.dumps(assistant_message, indent=2, default=str))
            
            tool_calls = assistant_message.get("tool_calls")

            if not tool_calls:
                print("WARNING:\nLLM returned text instead of tool call.")
                # No tool calls — Granite has a final answer
                final_response = assistant_message.get("content", "")
                self.cloudant.append_message(
                    session_id, {"role": "assistant", "content": final_response},
                )
                if on_event:
                    await self._emit(on_event, {"type": "ai_processing", "content": "Crafting your response..."})
                return final_response

            # Execute each tool call
            messages.append(assistant_message)

            for tool_call in tool_calls:
                function = tool_call["function"]
                tool_name = function["name"]

                try:
                    arguments = json.loads(function["arguments"])
                    if not isinstance(arguments, dict):
                        arguments = {}
                except Exception:
                    arguments = {}

                print("Tool Selected:")
                print(tool_name)
                print("Arguments:")
                print(json.dumps(arguments, indent=2))

                if on_event:
                    await self._emit(on_event, {
                        "type": "tool_start",
                        "tool_name": tool_name,
                        "tool_id": tool_call["id"],
                        "arguments": arguments,
                        "description": self._describe_tool_call(tool_name, arguments),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })

                start_time = time.time()
                tool_result = await self._execute_tool(tool_name, arguments, profile_id=profile_id)
                duration_ms = int((time.time() - start_time) * 1000)

                print("\n========================")
                print("Tool Result")
                print("========================")
                print(tool_result)

                if on_event:
                    await self._emit(on_event, {
                        "type": "tool_complete",
                        "tool_name": tool_name,
                        "tool_id": tool_call["id"],
                        "duration_ms": duration_ms,
                        "result_summary": self._summarize_tool_result(tool_name, tool_result),
                        "token_cost": self._estimate_token_cost(tool_name),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": tool_result,
                })

            print("\n========================")
            print("Conversation After Tool")
            print("========================")
            print(json.dumps(messages, indent=2, default=str))

        # If we exhausted iterations, return last assistant message
        final_response = "I found the information but couldn't complete the full analysis. Let me try again with a simpler approach."
        self.cloudant.append_message(
            session_id, {"role": "assistant", "content": final_response},
        )
        return final_response

    async def _emit(self, on_event, data):
        if asyncio.iscoroutinefunction(on_event):
            await on_event(data)
        else:
            on_event(data)

    def _describe_tool_call(self, tool_name: str, args: dict) -> str:
        """Human-readable description of what a tool call is doing."""
        descriptions = {
            "search_grants": f"Searching grants for {args.get('startup_stage', 'your')} stage startup in {', '.join(args.get('industries', ['agritech']))}",
            "get_grant_detail": f"Fetching details for grant: {args.get('grant_id', '')}",
            "match_profile": f"Running hybrid matching for {args.get('company_name', 'your startup')}",
            "check_eligibility": f"Checking eligibility for grant: {args.get('grant_id', '')}",
            "draft_proposal": f"Drafting proposal for grant: {args.get('grant_id', '')}",
            "explain_grant": f"Explaining grant: {args.get('grant_id', '')}",
            "semantic_search": f"Semantic search: \"{args.get('query', '')}\"",
        }
        return descriptions.get(tool_name, f"Running {tool_name}")

    def _summarize_tool_result(self, tool_name: str, result_json: str) -> str:
        """Brief summary of what a tool returned."""
        try:
            data = json.loads(result_json)
            if isinstance(data, list):
                return f"Found {len(data)} results"
            if isinstance(data, dict):
                if "error" in data:
                    return f"Error: {data['error'][:100]}"
                if "explanation" in data:
                    return "Explanation generated"
                if "eligible" in data:
                    return f"Eligible: {data['eligible']}, Score: {data.get('score', 'N/A')}"
                if "draft_content" in data or "executive_summary" in data:
                    return "Proposal draft generated"
                if "grant_name" in data:
                    return f"Grant: {data['grant_name']}"
            return f"Result: {len(result_json)} chars"
        except Exception:
            return f"Result: {len(result_json)} chars"

    def _estimate_token_cost(self, tool_name: str) -> int:
        """Estimated token cost for this tool execution."""
        costs = {
            "search_grants": 0,
            "get_grant_detail": 0,
            "match_profile": 5000,
            "check_eligibility": 1000,
            "draft_proposal": 4000,
            "explain_grant": 500,
            "semantic_search": 200,
        }
        return costs.get(tool_name, 0)


