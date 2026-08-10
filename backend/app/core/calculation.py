from typing import Dict, Any, List
from decimal import Decimal
from backend.app.schemas import FinancialCalculationResult


class CalculationEngine:
    def calculate(self, claim: Dict[str, Any], policy_raw: Dict[str, Any]) -> FinancialCalculationResult:
        category = str(claim.get("claim_category") or "").lower()
        category_policy = policy_raw.get("opd_categories", {}).get(category, {}) or {}
        claimed_amount = Decimal(str(claim.get("claimed_amount", 0)))

        if category.upper() == "DENTAL":
            approved_amount = Decimal("0")
            excluded = {str(item).lower() for item in category_policy.get("excluded_procedures", [])}
            covered = set()
            line_items = []
            for document in claim.get("documents", []):
                for item in (document.get("extracted", {}) or {}).get("line_items", []) or []:
                    description = str(item.get("description") or "")
                    amount = Decimal(str(item.get("amount", 0)))
                    is_excluded = any(exclusion in description.lower() for exclusion in excluded)
                    if is_excluded:
                        line_items.append({
                            "description": description,
                            "claimed_amount": str(amount),
                            "eligible": False,
                            "approved_amount": "0",
                            "reason": "Policy exclusion"
                        })
                        continue
                    approved_amount += amount
                    covered.add(description)
                    line_items.append({
                        "description": description,
                        "claimed_amount": str(amount),
                        "eligible": True,
                        "approved_amount": str(amount),
                        "reason": "Covered by policy"
                    })
            breakdown = {
                "covered_line_items": sorted(covered),
                "excluded_procedures": sorted(excluded),
                "line_items": line_items
            }
            decision_hint = "PARTIAL" if approved_amount > 0 else "REJECTED"
            return FinancialCalculationResult(approved_amount=approved_amount, decision_hint=decision_hint, breakdown=breakdown)

        hospital_name = claim.get("hospital_name")
        if not hospital_name:
            for d in claim.get("documents", []):
                if isinstance(d, dict) and d.get("extracted", {}).get("hospital_name"):
                    hospital_name = d["extracted"]["hospital_name"]
                    break
        hospital_name = str(hospital_name or "")
        
        network_hospitals = {str(hospital).lower().strip() for hospital in policy_raw.get("network_hospitals", [])}
        is_network = hospital_name.lower().strip() in network_hospitals if hospital_name else False
        amount = claimed_amount
        breakdown: Dict[str, Any] = {"claimed": str(claimed_amount), "network_applied": is_network}

        discount_pct = Decimal(str(category_policy.get("network_discount_percent", 0)))
        if is_network and discount_pct > 0:
            network_discount = (amount * discount_pct) / Decimal(100)
            amount -= network_discount
            breakdown["network_discount"] = str(network_discount)
        else:
            breakdown["network_discount"] = "0"

        copay_pct = Decimal(str(category_policy.get("copay_percent", 0)))
        copay = (amount * copay_pct) / Decimal(100)
        approved_amount = amount - copay
        breakdown["copay"] = str(copay)
        breakdown["approved"] = str(approved_amount)
        return FinancialCalculationResult(approved_amount=approved_amount, decision_hint="APPROVED", breakdown=breakdown)


