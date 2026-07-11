import json
from typing import Any
from dataclasses import dataclass

from apps.api.services.watsonx_service import WatsonxService
from apps.api.services.cloudant_service import CloudantService
from apps.api.services.embedding_service import EmbeddingService


@dataclass
class MatchResult:
    grant_id: str
    grant_name: str
    rule_score: float        # 0-1: from rule-based matching
    semantic_score: float    # 0-1: from embedding similarity
    ai_score: float          # 0-1: from Granite eligibility check
    final_score: float       # Weighted combination
    eligible: bool
    explanation: str
    met_criteria: list[str]
    unmet_criteria: list[str]
    grant_data: dict


class MatchingService:
    """
    Hybrid matching engine that combines:
    1. Rule-based filtering (fast, deterministic) — from existing agent_tools.py logic
    2. Semantic similarity (catches soft/fuzzy matches)
    3. AI eligibility assessment (nuanced understanding)
    """

    # Weights for hybrid scoring
    RULE_WEIGHT = 0.3
    SEMANTIC_WEIGHT = 0.3
    AI_WEIGHT = 0.4
    MAX_AI_CANDIDATES = 5  # Hard limit to control token spend

    def __init__(
        self,
        watsonx: WatsonxService,
        cloudant: CloudantService,
        embedding: EmbeddingService,
    ):
        self.watsonx = watsonx
        self.cloudant = cloudant
        self.embedding = embedding

    def _normalize(self, value: Any) -> str:
        return str(value).strip().casefold()

    def _normalize_list(self, values: list[Any]) -> set[str]:
        return {self._normalize(v) for v in values}

    # ==========================================
    # STEP 1: Rule-Based Scoring
    # ==========================================

    def _rule_score(self, grant: dict, profile: dict) -> dict:
        """
        Port of the existing agent_tools.py matching logic,
        but returns a detailed score breakdown dictionary.
        """
        max_score = 0.0
        met = []
        unmet = []
        
        breakdown = {
            "stage": 0.0,
            "industry": 0.0,
            "location": 0.0,
            "funding_type": 0.0,
            "amount": 0.0,
        }

        eligibility = grant.get("eligibility", {})
        funding = grant.get("funding", {})

        # --- Stage match (weight: 0.25) ---
        max_score += 0.25
        grant_stages = self._normalize_list(eligibility.get("startup_stages", []))
        profile_stage = self._normalize(profile.get("stage", "unknown"))

        if profile_stage in grant_stages or "all" in grant_stages or "any" in grant_stages:
            breakdown["stage"] = 0.25
            met.append(f"Stage '{profile_stage}' is eligible")
        else:
            unmet.append(f"Stage '{profile_stage}' not in {grant_stages}")

        # --- Industry match (weight: 0.25) ---
        max_score += 0.25
        grant_industries = self._normalize_list(eligibility.get("industries", []))
        profile_industries = self._normalize_list(profile.get("industries", []))

        industry_overlap = profile_industries & grant_industries
        if industry_overlap:
            breakdown["industry"] = 0.25
            met.append(f"Industry match: {', '.join(industry_overlap)}")
        elif "all sectors" in grant_industries:
            breakdown["industry"] = 0.25
            met.append("Grant is open to all sectors")
        else:
            unmet.append(f"No industry overlap between {profile_industries} and {grant_industries}")

        # --- Location match (weight: 0.25) ---
        max_score += 0.25
        grant_locations = self._normalize_list(eligibility.get("allowed_locations", []))
        
        raw_loc = profile.get("location", {})
        if isinstance(raw_loc, dict):
            profile_location = self._normalize(raw_loc.get("country", ""))
            profile_state = self._normalize(raw_loc.get("state", ""))
        else:
            profile_location = self._normalize(raw_loc)
            profile_state = ""

        if (
            profile_location in grant_locations
            or profile_state in grant_locations
            or "global" in grant_locations
            or "worldwide" in grant_locations
            or "any" in grant_locations
        ):
            breakdown["location"] = 0.25
            met.append(f"Location '{profile_location}' is eligible")
        else:
            unmet.append(f"Location '{profile_location}' not in {grant_locations}")

        # --- Funding type match (weight: 0.15) ---
        max_score += 0.15
        grant_funding_type = self._normalize(funding.get("funding_type", "unknown"))
        profile_funding_types = self._normalize_list(
            profile.get("funding_needed", {}).get("types", [])
        )

        if not profile_funding_types or grant_funding_type in profile_funding_types:
            breakdown["funding_type"] = 0.15
            met.append(f"Funding type '{grant_funding_type}' matches preference")
        else:
            unmet.append(f"Funding type '{grant_funding_type}' not in preferred types")

        # --- Amount check (weight: 0.10) ---
        max_score += 0.10
        needed = profile.get("funding_needed", {}).get("amount")
        maximum = funding.get("maximum_amount")
        minimum = funding.get("minimum_amount")

        if needed is None:
            breakdown["amount"] = 0.10
            met.append("No specific funding amount requested")
        else:
            is_valid = True
            if maximum is not None and needed > maximum:
                is_valid = False
                unmet.append(f"Needed {needed} > Max {maximum}")
            if minimum is not None and needed < minimum:
                is_valid = False
                unmet.append(f"Needed {needed} < Min {minimum}")
                
            if is_valid:
                breakdown["amount"] = 0.10
                met.append("Funding amount is within grant limits")

        total_score = sum(breakdown.values())
        breakdown["total"] = total_score / max_score if max_score > 0 else 0.0
        breakdown["met"] = met
        breakdown["unmet"] = unmet
        
        return breakdown

    # ==========================================
    # STEP 2: Full Hybrid Match
    # ==========================================

    async def match_profile_to_grants(
        self,
        profile: dict,
        top_n: int = 10,
        use_ai_assessment: bool = True,
    ) -> list[MatchResult]:
        """
        Full hybrid matching pipeline:
        1. Get all active grants from Cloudant
        2. Run rule-based scoring on all
        3. Run semantic search
        4. Merge scores
        5. (Optional) Run AI assessment on top candidates
        6. Return ranked results
        """

        # Step 1: Get all grants
        all_grants = self.cloudant.get_all_active_grants(limit=200)

        # Step 2: Rule-based scoring
        rule_scores: dict[str, dict] = {}
        for grant in all_grants:
            gid = grant.get("_id", "")
            rule_scores[gid] = self._rule_score(grant, profile)

        # Step 3: Semantic search
        description = profile.get('description', '').strip()
        if description:
            # Rich semantic query
            raw_loc = profile.get('location', {})
            loc_str = raw_loc.get('country', 'India') if isinstance(raw_loc, dict) else raw_loc
            query_parts = [
                f"Company: {profile.get('company_name', 'Unknown')}",
                f"Industry: {', '.join(profile.get('industries', []))}",
                f"Stage: {profile.get('stage', 'unknown')}",
                f"Location: {loc_str}",
                f"Description: {description}",
            ]
            funding_needed = profile.get("funding_needed", {})
            if funding_needed.get("types"):
                query_parts.append(f"Looking for: {', '.join(funding_needed['types'])}")
            query = "\n".join(query_parts)
            
            sem_weight = self.SEMANTIC_WEIGHT
            rule_weight = self.RULE_WEIGHT
        else:
            # Fallback for empty descriptions
            query = f"Startup in {', '.join(profile.get('industries', []))} at {profile.get('stage', 'unknown')} stage."
            sem_weight = 0.0
            rule_weight = self.RULE_WEIGHT + self.SEMANTIC_WEIGHT
            
        
        semantic_results = self.embedding.search_similar_grants(query, limit=50)
        semantic_scores: dict[str, float] = {}
        if semantic_results and semantic_results["ids"] and semantic_results["ids"][0]:
            for i, doc_id in enumerate(semantic_results["ids"][0]):
                distance = semantic_results["distances"][0][i] if semantic_results["distances"] else 0
                similarity = 1.0 - distance
                semantic_scores[doc_id] = similarity

        # Step 4: Merge into candidates
        candidates: list[dict] = []
        grants_by_id = {g["_id"]: g for g in all_grants}

        all_grant_ids = set(rule_scores.keys()) | set(semantic_scores.keys())

        import logging
        logger = logging.getLogger(__name__)

        for gid in all_grant_ids:
            r_dict = rule_scores.get(gid, {"total": 0.0, "met": [], "unmet": [], "stage": 0.0, "industry": 0.0, "location": 0.0, "amount": 0.0, "funding_type": 0.0})
            r_score = r_dict["total"]
            met = r_dict.get("met", [])
            unmet = r_dict.get("unmet", [])
            s_score = semantic_scores.get(gid, 0.0)

            # Pre-AI combined score for ranking (Mathematically sound)
            # Normalizing by the sum of rule and sem weights
            weight_sum = rule_weight + sem_weight
            combined = (rule_weight * r_score + sem_weight * s_score) / weight_sum if weight_sum > 0 else 0.0
            
            # Score Explainability Logging
            logger.debug(
                f"Grant: {grants_by_id.get(gid, {}).get('grant_name', gid)} | "
                f"Sem: {s_score:.2f} | Ind: {r_dict.get('industry', 0.0):.2f} | "
                f"Stage: {r_dict.get('stage', 0.0):.2f} | Loc: {r_dict.get('location', 0.0):.2f} | "
                f"FundType: {r_dict.get('funding_type', 0.0):.2f} | Amount: {r_dict.get('amount', 0.0):.2f} | "
                f"PreAITotal: {combined:.2f}"
            )

            candidates.append({
                "grant_id": gid,
                "rule_score": r_score,
                "semantic_score": s_score,
                "combined": combined,
                "met": met,
                "unmet": unmet,
            })

        # Sort by combined score, take top candidates for AI assessment
        candidates.sort(key=lambda c: c["combined"], reverse=True)
        top_candidates = candidates[:self.MAX_AI_CANDIDATES]  # COST: limit AI calls

        # Step 5: AI eligibility assessment on top candidates ONLY
        results: list[MatchResult] = []

        for candidate in top_candidates:
            gid = candidate["grant_id"]
            grant = grants_by_id.get(gid)
            if not grant:
                continue

            ai_score = candidate["rule_score"]  # Default fallback
            ai_eligible = candidate["rule_score"] > 0.5
            explanation = ""

            if use_ai_assessment:
                try:
                    ai_result = self.watsonx.check_eligibility(grant, profile)
                    ai_score = ai_result.get("score", 0.0)
                    ai_eligible = ai_result.get("eligible", False)
                    explanation = ai_result.get("recommendation", "")
                    candidate["met"].extend(ai_result.get("met_criteria", []))
                    candidate["unmet"].extend(ai_result.get("unmet_criteria", []))
                except Exception:
                    pass  # Fall back to rule-based score

            # Final weighted score
            final_score = (
                rule_weight * candidate["rule_score"]
                + sem_weight * candidate["semantic_score"]
                + self.AI_WEIGHT * ai_score
            )
            
            logger.debug(f"Final Score for {grant.get('grant_name', '')}: {final_score:.2f} (AI Score: {ai_score:.2f})")

            results.append(MatchResult(
                grant_id=gid,
                grant_name=grant.get("grant_name", ""),
                rule_score=candidate["rule_score"],
                semantic_score=candidate["semantic_score"],
                ai_score=ai_score,
                final_score=round(final_score, 4),
                eligible=ai_eligible,
                explanation=explanation,
                met_criteria=list(set(candidate["met"])),
                unmet_criteria=list(set(candidate["unmet"])),
                grant_data=grant,
            ))

        # Sort by final score
        results.sort(key=lambda r: r.final_score, reverse=True)

        return results
