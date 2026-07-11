import json
import logging
import time
from typing import Any, List, Dict
import google.genai as genai
from google.genai import types
from google.genai.errors import ClientError

from ibm_watsonx_ai import APIClient, Credentials
from ibm_watsonx_ai.foundation_models import ModelInference, Embeddings
from shared.prompts.matching_prompts import ELIGIBILITY_CHECK_PROMPT, MATCH_EXPLANATION_PROMPT

logger = logging.getLogger(__name__)

class WatsonxService:
    def __init__(
        self,
        api_key: str,
        project_id: str,
        url: str,
        chat_model_id: str = "ibm/granite-4-h-small",
        embedding_model_id: str = "ibm/granite-embedding-278m-multilingual",
        gemini_api_key: str = None
    ):
        self.watsonx_api_key = api_key
        self.watsonx_project_id = project_id
        self.watsonx_url = url
        self.chat_model_id = chat_model_id
        self.embedding_model_id = embedding_model_id
        
        self.gemini_api_key = gemini_api_key
        self.gemini_client = None
        if self.gemini_api_key:
            try:
                self.gemini_client = genai.Client(api_key=self.gemini_api_key)
            except Exception as e:
                logger.error(f"Failed to initialize Gemini: {e}")

    def get_chat_model(self) -> ModelInference:
        credentials = Credentials(url=self.watsonx_url, api_key=self.watsonx_api_key)
        client = APIClient(credentials=credentials, project_id=self.watsonx_project_id)
        return ModelInference(model_id=self.chat_model_id, api_client=client)
        
    def get_embeddings_model(self) -> Embeddings:
        credentials = Credentials(url=self.watsonx_url, api_key=self.watsonx_api_key)
        client = APIClient(credentials=credentials, project_id=self.watsonx_project_id)
        return Embeddings(model_id=self.embedding_model_id, api_client=client)

    def _convert_messages_to_gemini(self, messages: list[dict]) -> tuple[list[types.Content], str]:
        gemini_messages = []
        system_prompts = []
        
        def get_tool_name_by_id(tool_call_id: str, msgs: list) -> str:
            for msg in reversed(msgs):
                if msg.get("role") == "assistant" and msg.get("tool_calls"):
                    for tc in msg["tool_calls"]:
                        if tc.get("id") == tool_call_id:
                            return tc["function"]["name"]
            return "unknown_tool"
            
        for m in messages:
            if m.get("role") == "system":
                if m.get("content"):
                    system_prompts.append(m["content"])
                continue
                
            role = m.get("role", "user")
            parts = []
            
            if role == "tool":
                tool_call_id = m.get("tool_call_id")
                tool_name = get_tool_name_by_id(tool_call_id, messages)
                raw_content = m.get("content", "")
                try:
                    response_data = json.loads(raw_content)
                    if not isinstance(response_data, dict):
                        response_data = {"result": response_data}
                except Exception:
                    response_data = {"result": raw_content}
                
                parts.append(
                    types.Part(
                        function_response=types.FunctionResponse(
                            name=tool_name,
                            response=response_data,
                            id=tool_call_id
                        )
                    )
                )
                role = "user"
            elif role == "assistant" and m.get("tool_calls"):
                for tc in m["tool_calls"]:
                    if "_gemini_part" in tc and tc["_gemini_part"]:
                        try:
                            parts.append(types.Part.model_validate(tc["_gemini_part"]))
                            continue
                        except Exception as e:
                            logger.warning(f"Failed to validate _gemini_part: {e}")
                            
                    args_raw = tc["function"]["arguments"]
                    if isinstance(args_raw, str):
                        try:
                            args = json.loads(args_raw)
                        except Exception:
                            args = {}
                    else:
                        args = args_raw or {}
                    parts.append(
                        types.Part(
                            function_call=types.FunctionCall(
                                name=tc["function"]["name"],
                                args=args
                            )
                        )
                    )
                role = "model"
            else:
                if role == "assistant":
                    role = "model"
                elif role not in ["user", "model"]:
                    role = "user"
                parts.append(types.Part.from_text(text=m.get("content", "")))
            
            gemini_messages.append(types.Content(role=role, parts=parts))
            
        system_prompt = "\n".join(system_prompts)
        return gemini_messages, system_prompt

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> Any:
        if self.gemini_client:
            gemini_messages, system_prompt = self._convert_messages_to_gemini(messages)
            
            models_to_try = [
                'gemini-3.1-flash-lite'
            ]
            last_error = None
            for model_name in models_to_try:
                try:
                    response = self.gemini_client.models.generate_content(
                        model=model_name,
                        contents=gemini_messages,
                        config=types.GenerateContentConfig(
                            system_instruction=system_prompt if system_prompt else None,
                            temperature=kwargs.get("params", {}).get("temperature", 0.2)
                        )
                    )
                    logger.info(f"chat: succeeded with {model_name}")
                    return {"choices": [{"message": {"role": "assistant", "content": response.text}}]}
                except ClientError as e:
                    if e.code == 429:
                        logger.warning(f"chat: {model_name} quota exhausted (daily limit hit), skipping")
                    else:
                        logger.warning(f"chat: {model_name} failed ({e.code}): {e}")
                    last_error = e
                except Exception as e:
                    logger.warning(f"chat: {model_name} failed: {e}")
                    last_error = e
            raise RuntimeError(f"All Gemini models failed. Last error: {last_error}")
        
        model = self.get_chat_model()
        return model.chat(messages=messages, **kwargs)

    def _convert_tools_to_gemini(self, tools: list[dict]) -> list[types.Tool]:
        gemini_tools = []
        for t in tools:
            func = t["function"]
            props = func.get("parameters", {}).get("properties", {})
            required = func.get("parameters", {}).get("required", [])
            
            gemini_props = {}
            for k, v in props.items():
                ptype = types.Type.STRING
                if v.get("type") == "integer": ptype = types.Type.INTEGER
                elif v.get("type") == "boolean": ptype = types.Type.BOOLEAN
                elif v.get("type") == "number": ptype = types.Type.NUMBER
                
                gemini_props[k] = types.Schema(
                    type=ptype,
                    description=v.get("description", "")
                )
                
            gemini_func = types.FunctionDeclaration(
                name=func["name"],
                description=func.get("description", ""),
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties=gemini_props,
                    required=required
                ) if props else None
            )
            gemini_tools.append(types.Tool(function_declarations=[gemini_func]))
        return gemini_tools

    def chat_with_tools(self, messages: list[dict], tools: list[dict], max_tokens: int = 2000) -> dict:
        if self.gemini_client:
            gemini_messages, system_prompt = self._convert_messages_to_gemini(messages)
            gemini_tools = self._convert_tools_to_gemini(tools)
            
            models_to_try = [
                'gemini-3.1-flash-lite',
               
            ]
            last_error = None
            for model_name in models_to_try:
                try:
                    response = self.gemini_client.models.generate_content(
                        model=model_name,
                        contents=gemini_messages,
                        config=types.GenerateContentConfig(
                            system_instruction=system_prompt if system_prompt else None,
                            tools=gemini_tools,
                            temperature=0.2
                        )
                    )
                    
                    # Check for function call
                    if response.function_calls:
                        call = response.function_calls[0]
                        
                        # Find the original Part to preserve thought_signature and other internal fields
                        original_part_dict = None
                        if hasattr(response, 'candidates') and response.candidates:
                            content = getattr(response.candidates[0], 'content', None)
                            if content and hasattr(content, 'parts') and content.parts:
                                for p in content.parts:
                                    if hasattr(p, 'function_call') and p.function_call and p.function_call.name == call.name:
                                        try:
                                            original_part_dict = p.model_dump(exclude_none=True)
                                        except Exception:
                                            pass
                                        break
                                        
                        # Convert to Watsonx format
                        args = dict(call.args) if call.args else {}
                        tool_call = {
                            "id": getattr(call, "id", f"call_{int(time.time())}"),
                            "type": "function",
                            "function": {
                                "name": call.name,
                                "arguments": json.dumps(args)
                            }
                        }
                        if original_part_dict:
                            tool_call["_gemini_part"] = original_part_dict
                            
                        logger.info(f"chat_with_tools: succeeded with {model_name} (tool call)")
                        return {"choices": [{"message": {"role": "assistant", "tool_calls": [tool_call]}}]}
                    
                    # Normal text response
                    logger.info(f"chat_with_tools: succeeded with {model_name} (text)")
                    return {"choices": [{"message": {"role": "assistant", "content": response.text}}]}

                except ClientError as e:
                    if e.code == 429:
                        logger.warning(f"chat_with_tools: {model_name} quota exhausted (daily limit hit), skipping")
                    else:
                        logger.warning(f"chat_with_tools: {model_name} failed ({e.code}): {e}")
                    last_error = e
                except Exception as e:
                    logger.warning(f"chat_with_tools: {model_name} failed: {e}")
                    last_error = e
            raise RuntimeError(f"All Gemini models failed. Last error: {last_error}")

        # Fallback to Watsonx
        model = self.get_chat_model()
        return model.chat(messages=messages, tools=tools, params={"max_tokens": max_tokens, "temperature": 0.2})

    def get_response_text(self, response: Any) -> str:
        try:
            return response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            return str(response)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if self.gemini_client:
            try:
                response = self.gemini_client.models.embed_content(
                    model='gemini-embedding-001',
                    contents=texts
                )
                return [emb.values for emb in response.embeddings]
            except Exception as e:
                logger.warning(f"Gemini embed_texts failed: {e}")
        return self.get_embeddings_model().embed_documents(texts)

    def embed_query(self, query: str) -> list[float]:
        if self.gemini_client:
            try:
                response = self.gemini_client.models.embed_content(
                    model='gemini-embedding-001',
                    contents=query
                )
                return response.embeddings[0].values
            except Exception as e:
                logger.warning(f"Gemini embed_query failed: {e}")
        return self.get_embeddings_model().embed_query(query)

    def check_eligibility(self, grant: dict, profile: dict) -> dict:
        messages = [
            {"role": "system", "content": ELIGIBILITY_CHECK_PROMPT},
            {"role": "user", "content": f"Grant:\n{json.dumps(grant)}\n\nProfile:\n{json.dumps(profile)}"}
        ]
        response = self.chat(messages, params={"max_tokens": 1000})
        content = self.get_response_text(response)
        try:
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            return json.loads(content.strip())
        except Exception:
            return {"eligible": False, "score": 0.0, "recommendation": "Could not verify eligibility."}

    def explain_grant(self, grant: dict) -> str:
        messages = [
            {"role": "system", "content": MATCH_EXPLANATION_PROMPT},
            {"role": "user", "content": f"Please explain this grant:\n{json.dumps(grant)}"}
        ]
        response = self.chat(messages, params={"max_tokens": 500})
        return self.get_response_text(response)
