from decimal import Decimal
from datetime import datetime, timedelta
import re
from typing import Dict, Any, List, Optional
from .policy import PolicyRepository
from .adapter import normalize_claim_input
from .identity import normalize_identity_name
from .schemas import PolicyEvaluation, RuleResult


def _parse_date(d: str) -> datetime:
    return datetime.fromisoformat(d)


class PolicyEvaluator:
    def __init__(self, policy_repo: PolicyRepository):
        self.repo = policy_repo
        # ensure raw policy loaded and keep raw dict for lookups
        # PolicyRepository.load() returns a PolicySnapshot but also stores the raw policy in ._policy
        snapshot = self.repo.load()
        # attempt to get raw policy dict
        raw = getattr(self.repo, "_policy", None)
        if raw is None:
            # fallback: use snapshot.model_dump() but keep coverage only
            raw = snapshot.model_dump(mode="python")
        self.policy = raw

    def evaluate(self, claim: Dict[str, Any]) -> PolicyEvaluation:
        claim = normalize_claim_input(claim)
        policy_id = claim.get("policy_id")
        checks: List[RuleResult] = []

        # 1. policy period
        start = self.policy.get("policy_holder", {}).get("policy_start_date") or self.policy.get("policy_start_date")
        end = self.policy.get("policy_holder", {}).get("policy_end_date") or self.policy.get("policy_end_date")
        treatment_date = claim.get("treatment_date")
        ok = True
        details = {}
        try:
            if start and end and treatment_date:
                sd = _parse_date(start)
                ed = _parse_date(end)
                td = _parse_date(treatment_date)
                ok = (sd.date() <= td.date() <= ed.date())
                details = {"policy_start": start, "policy_end": end, "treatment_date": treatment_date}
        except Exception:
            ok = False
            details = {"error": "invalid_date_format"}

        checks.append(RuleResult(name="policy_period", ok=bool(ok), details=details))

        # 2. member eligibility (join date)
        member_id = claim.get("member_id")
        member = None
        for m in self.policy.get("members", []):
            if m.get("member_id") == member_id:
                member = m
                break
        if member is None:
            checks.append(RuleResult(name="member_exists", ok=False, details={"member_id": member_id}))
        else:
            join_date = member.get("join_date")
            ok = True
            details = {"join_date": join_date}
            try:
                if join_date and treatment_date:
                    jd = _parse_date(join_date)
                    td = _parse_date(treatment_date)
                    ok = jd.date() <= td.date()
            except Exception:
                ok = False
                details = {"error": "invalid_date_format"}
            checks.append(RuleResult(name="member_eligibility", ok=bool(ok), details=details))

        # 3. category coverage and document requirements
        category = claim.get("claim_category") or ""
        category_key = category.lower()
        opd = self.policy.get("opd_categories", {})
        cat_policy = opd.get(category_key)
        if not cat_policy:
            checks.append(RuleResult(name="category_coverage", ok=False, details={"category": category}))
        else:
            checks.append(RuleResult(name="category_coverage", ok=bool(cat_policy.get("covered", False)), details={"category": category, "policy": cat_policy}))

        # 4. document requirements (normalized by the fixture adapter)
        doc_reqs = self.policy.get("document_requirements", {})
        reqs = doc_reqs.get(category.upper(), {})
        required = reqs.get("required", [])
        provided = []
        for d in claim.get("documents", []):
            at = d.get("document_type")
            quality = d.get("quality")
            # treat unreadable documents as not provided
            if at and (quality is None or str(quality).upper() != "UNREADABLE"):
                provided.append(at)
        missing = [r for r in required if r not in provided]
        ok = len(missing) == 0
        checks.append(RuleResult(name="document_requirements", ok=ok, details={"required": required, "provided": provided, "missing": missing}))

        # 5. per-claim limit
        per_claim_limit = self.policy.get("coverage", {}).get("per_claim_limit")
        claimed_amount = Decimal(str(claim.get("claimed_amount", "0")))
        ok = True
        if per_claim_limit is not None:
            limit = Decimal(str(per_claim_limit))
            ok = claimed_amount <= limit
        checks.append(RuleResult(name="per_claim_limit", ok=ok, details={"limit": per_claim_limit, "claimed_amount": str(claimed_amount)}))

        # 6. category/sub-limits. A category limit is cumulative, unlike the
        # explicit per-claim limit above; do not reject from a single claim when
        # category utilisation was not supplied.
        ok = True
        details = {}
        if cat_policy:
            sub_limit = cat_policy.get("sub_limit")
            if sub_limit is not None:
                sub = Decimal(str(sub_limit))
                category_ytd = claim.get("category_ytd_claims_amount")
                if category_ytd is not None:
                    category_ytd_amount = Decimal(str(category_ytd))
                    ok = category_ytd_amount + claimed_amount <= sub
                    details = {"sub_limit": str(sub_limit), "category_ytd": str(category_ytd_amount), "claimed_amount": str(claimed_amount)}
                else:
                    details = {"sub_limit": str(sub_limit), "status": "UTILISATION_NOT_PROVIDED"}
        checks.append(RuleResult(name="category_sub_limit", ok=ok, details=details))

        # 7. annual limit (simple YTD check if ytd_claims_amount provided)
        annual_limit = self.policy.get("coverage", {}).get("annual_opd_limit")
        ytd = Decimal(str(claim.get("ytd_claims_amount", 0)))
        ok = True
        if annual_limit is not None:
            annual = Decimal(str(annual_limit))
            ok = (ytd + claimed_amount) <= annual
        checks.append(RuleResult(name="annual_limit", ok=ok, details={"annual_limit": annual_limit, "ytd": str(ytd), "claimed_amount": str(claimed_amount)}))

        minimum = self.policy.get("submission_rules", {}).get("minimum_claim_amount")
        minimum_ok = minimum is None or claimed_amount >= Decimal(str(minimum))
        checks.append(RuleResult(name="minimum_claim_amount", ok=minimum_ok, details={"minimum": minimum, "claimed_amount": str(claimed_amount)}))

        # 8b. fraud signals (simple same-day/monthly checks if history provided)
        fraud_thresholds = self.policy.get("fraud_thresholds", {})
        fraud_issues = []
        history = claim.get("claims_history", []) or []
        if history and treatment_date:
            same_day = 0
            for h in history:
                try:
                    # prefer simple string equality for robust matching
                    if str(h.get("date")) == str(treatment_date):
                        same_day += 1
                        continue
                    hd = _parse_date(h.get("date")).date()
                    td = _parse_date(treatment_date).date()
                    if hd == td:
                        same_day += 1
                except Exception:
                    continue
            if same_day >= int(fraud_thresholds.get("same_day_claims_limit", 9999)):
                fraud_issues.append({"type": "same_day_claims", "count": same_day})
        checks.append(RuleResult(name="fraud_signals", ok=(len(fraud_issues) == 0), details={"issues": fraud_issues}))

        # 8. waiting periods and specific conditions
        wp = self.policy.get("waiting_periods", {})
        waiting_issues = []
        # check initial waiting
        initial_days = wp.get("initial_waiting_period_days")
        if initial_days and member and member.get("join_date"):
            jd = _parse_date(member.get("join_date"))
            eligible_initial = jd + timedelta(days=int(initial_days))
            td = _parse_date(treatment_date)
            if td < eligible_initial:
                waiting_issues.append({"type": "initial_waiting_period", "eligible_from": eligible_initial.date().isoformat()})

        # check specific conditions by scanning document diagnosis fields
        specific = wp.get("specific_conditions", {})
        diag_text = ""
        for d in claim.get("documents", []):
            content = d.get("extracted") or {}
            diag = content.get("diagnosis") or content.get("diagnoses")
            if diag:
                diag_text += " " + str(diag)
        diag_text = diag_text.lower()
        for cond, days in specific.items():
            if re.search(rf"\b{re.escape(cond.lower())}\b", diag_text):
                # compute eligible date
                jd = _parse_date(member.get("join_date")) if member and member.get("join_date") else None
                if jd:
                    eligible = jd + timedelta(days=int(days))
                    td = _parse_date(treatment_date)
                    if td < eligible:
                        waiting_issues.append({"type": "specific_condition", "condition": cond, "eligible_from": eligible.date().isoformat()})

        checks.append(RuleResult(name="waiting_periods", ok=(len(waiting_issues) == 0), details={"issues": waiting_issues}))

        # 9. exclusions — look for excluded conditions in diagnosis or procedures
        exclusions = self.policy.get("exclusions", {})
        excluded_conditions = exclusions.get("conditions", [])
        found_exclusions = []
        for ex in excluded_conditions:
            key = ex.lower()
            if key.split()[0] in diag_text or key in diag_text:
                found_exclusions.append(ex)
        checks.append(RuleResult(name="exclusions", ok=(len(found_exclusions) == 0), details={"found_exclusions": found_exclusions}))

        # 10. pre-authorization
        pre_auth_conf = self.policy.get("pre_authorization", {})
        pre_auth_required = False
        pre_auth_reasons = []
        # e.g., MRI/CT amount thresholds
        # inspect line_items
        for d in claim.get("documents", []):
            content = d.get("extracted") or {}
            items = content.get("line_items") or []
            for it in items:
                desc = (it.get("description") or "").lower()
                amt = Decimal(str(it.get("amount") or 0))
                if ("mri" in desc or "ct" in desc) and amt > Decimal(str(cat_policy.get("pre_auth_threshold", 0))):
                    pre_auth_required = True
                    pre_auth_reasons.append({"item": desc, "amount": str(amt), "threshold": cat_policy.get("pre_auth_threshold")})

        # if any pre_auth required, check provided documents for pre-auth evidence (we don't have preauth doc type; assume missing)
        ok = True
        if pre_auth_required:
            ok = False
        checks.append(RuleResult(name="pre_authorization", ok=ok, details={"required": pre_auth_required, "reasons": pre_auth_reasons}))

        # 11. network hospital lookup
        network_hospitals = [h.lower() for h in self.policy.get("network_hospitals", [])]
        hospital_name = claim.get("hospital_name")
        is_network = False
        if hospital_name:
            is_network = any(hospital_name.lower() == n for n in network_hospitals)
        checks.append(RuleResult(name="network_hospital", ok=is_network, details={"hospital": hospital_name, "is_network": is_network}))

        # 12. cross-document identity consistency
        raw_names: List[str] = []
        normalized_names = set()
        for d in claim.get("documents", []):
            pn = (d.get("extracted") or {}).get("patient_name")
            if pn:
                raw_names.append(str(pn).strip())
                normalized_names.add(normalize_identity_name(str(pn)))
        identity_ok = len(normalized_names) <= 1
        checks.append(
            RuleResult(
                name="identity_consistency",
                ok=identity_ok,
                details={"found_names": sorted(set(raw_names))},
            )
        )

        return PolicyEvaluation(policy_id=policy_id or self.policy.get("policy_id"), checks=checks)
