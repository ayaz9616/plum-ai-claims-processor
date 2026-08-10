
import re
import unicodedata

def normalize_identity_name(name: str) -> str:
    """Canonical, conservative identity comparison for OCR/document variations."""
    name = unicodedata.normalize("NFKC", str(name or ""))
    name = re.sub(r"^(mr|ms|mrs|dr)\.?\s*", "", name, flags=re.IGNORECASE)
    name = re.sub(r"[^\w\s]", " ", name.casefold())
    return " ".join(name.split())

from typing import Dict, Any, Optional
from backend.app.schemas import MemberResolutionResult



class MemberResolver:
    """Resolve member and policy validity using policy_terms.json data."""
    def resolve(self, claim: Dict[str, Any], policy_raw: Dict[str, Any]) -> MemberResolutionResult:
        member_id = claim.get("member_id")
        policy_id = claim.get("policy_id")
        treatment_date_str = claim.get("treatment_date")
        errors = []
        if not policy_raw or policy_raw.get("policy_id") != policy_id:
            errors.append(f"Policy not found or mismatch: {policy_id}")
            return MemberResolutionResult(
                member_id=str(member_id), member_name="", member_found=False,
                policy_id=str(policy_id), policy_valid=False, eligible=False, errors=errors)
        # Date validity
        try:
            td = datetime.fromisoformat(treatment_date_str).date()
            start = policy_raw.get("policy_holder", {}).get("policy_start_date") or policy_raw.get("policy_start_date")
            end = policy_raw.get("policy_holder", {}).get("policy_end_date") or policy_raw.get("policy_end_date")
            if start and end:
                sd = datetime.fromisoformat(start).date()
                ed = datetime.fromisoformat(end).date()
                if not (sd <= td <= ed):
                    errors.append("Treatment date outside policy period")
        except Exception:
            pass
        members = policy_raw.get("members", [])
        found_member = next((m for m in members if m.get("member_id") == member_id), None)
        if not found_member:
            errors.append(f"Member {member_id} not found in policy")
            return MemberResolutionResult(
                member_id=str(member_id), member_name="", member_found=False,
                policy_id=str(policy_id), policy_valid=True, eligible=False, errors=errors)
        primary_member = found_member
        if found_member.get("relationship") != "SELF":
            primary_id = found_member.get("primary_member_id")
            primary_member = next((m for m in members if m.get("member_id") == primary_id), None)
            if not primary_member or found_member.get("member_id") not in primary_member.get("dependents", []):
                errors.append("Invalid dependent relationship")
        try:
            if primary_member and primary_member.get("join_date") and treatment_date_str:
                jd = datetime.fromisoformat(primary_member.get("join_date")).date()
                td = datetime.fromisoformat(treatment_date_str).date()
                if jd > td:
                    errors.append("Treatment date before join date")
        except Exception:
            pass
        dependent_records = [
            {"dependent_id": dependent.get("member_id"), "name": dependent.get("name"), "relationship": dependent.get("relationship"), "primary_member_id": dependent.get("primary_member_id")}
            for dependent in members if dependent.get("primary_member_id") == found_member.get("member_id")
        ] if found_member.get("relationship") == "SELF" else []
        return MemberResolutionResult(
            member_id=str(member_id), member_name=found_member.get("name", ""), member_found=True,
            policy_id=str(policy_id), policy_valid=True, eligible=len(errors) == 0,
            dependents=dependent_records,
            errors=errors
        )


