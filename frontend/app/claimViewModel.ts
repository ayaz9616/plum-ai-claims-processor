import type { ClaimProcessingResult, ClaimSubmission, TraceEvent } from "./types";
import { formatCurrency } from "./utils";

export type FinancialViewModel = {
  claimed: number;
  approved: number;
  excluded: number;
  networkApplied: boolean;
  networkDiscount: number;
  copay: number;
  copayPercent?: number;
  lineItems: Array<Record<string, unknown>>;
  isDental: boolean;
  estimated: boolean;
};

export type ClaimViewModel = {
  claimId: string;
  patientName: string;
  memberId: string;
  claimCategory: string;
  claimCategoryLabel: string;
  treatmentDate: string;
  treatmentDateLabel: string;
  claimedAmount: number;
  policyId: string;
  hospital: string;
  financial: FinancialViewModel | null;
  memberResolution?: TraceEvent;
  memberDocumentConsistency?: TraceEvent;
  crossDocumentConsistency?: TraceEvent;
  documentVerification?: TraceEvent;
  documentExtraction?: TraceEvent;
  policyEvaluation?: TraceEvent;
  financialCalculation?: TraceEvent;
  fraudAnalysis?: TraceEvent;
};

function traceStep(result: ClaimProcessingResult, step: string): TraceEvent | undefined {
  return result.trace.find((event) => event.step === step);
}

function formatDisplayDate(value: string | undefined): string {
  if (!value) return "Not available";
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return value;
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(date);
}

function formatCategoryLabel(category: string): string {
  if (!category) return "Not available";
  return category
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function toNumber(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function inputFromTrace(result: ClaimProcessingResult): Record<string, unknown> {
  const inputValidation = traceStep(result, "INPUT_VALIDATION");
  return (inputValidation?.safe_input as Record<string, unknown>) || {};
}

function extractedHospital(extraction?: TraceEvent): string | undefined {
  const documents = extraction?.safe_output;
  if (!Array.isArray(documents)) return undefined;
  for (const document of documents) {
    const hospital =
      document?.extracted?.hospital_name ||
      document?.extracted?.provider_name ||
      document?.hospital_name;
    if (hospital) return String(hospital);
  }
  return undefined;
}

function buildFinancialViewModel(
  result: ClaimProcessingResult,
  submission: ClaimSubmission,
  financeTrace?: TraceEvent,
  policyTrace?: TraceEvent,
): FinancialViewModel | null {
  const breakdown = financeTrace?.safe_output?.breakdown as Record<string, unknown> | undefined;
  if (!breakdown) return null;

  const lineItems = Array.isArray(breakdown.line_items) ? breakdown.line_items : [];
  const input = inputFromTrace(result);
  const claimed =
    toNumber(submission.claimed_amount) ??
    toNumber(input.claimed_amount) ??
    toNumber(breakdown.claimed) ??
    0;

  const approvedFromResult = toNumber(result.approved_amount);
  const approvedFromBreakdown = toNumber(breakdown.approved);
  const approvedFromLineItems = lineItems.reduce((sum, item) => {
    const amount = toNumber(item.approved_amount) ?? (item.eligible === false ? 0 : toNumber(item.claimed_amount));
    return sum + (amount ?? 0);
  }, 0);

  const approved =
    approvedFromResult ??
    approvedFromBreakdown ??
    (lineItems.length > 0 ? approvedFromLineItems : 0);

  const excludedFromLineItems = lineItems.reduce((sum, item) => {
    if (item.eligible === false) {
      return sum + (toNumber(item.claimed_amount) ?? 0);
    }
    return sum;
  }, 0);

  const excluded =
    excludedFromLineItems > 0
      ? excludedFromLineItems
      : Math.max(claimed - approved, 0);

  const categoryCoverage = (policyTrace?.safe_output?.checks as Array<{ name?: string; details?: Record<string, unknown> }> | undefined)?.find(
    (check) => check.name === "category_coverage",
  )?.details?.policy as Record<string, unknown> | undefined;

  const isDental =
    lineItems.length > 0 &&
    breakdown.claimed === undefined &&
    breakdown.copay === undefined;

  return {
    claimed,
    approved,
    excluded,
    networkApplied: Boolean(breakdown.network_applied),
    networkDiscount: toNumber(breakdown.network_discount) ?? 0,
    copay: toNumber(breakdown.copay) ?? 0,
    copayPercent: toNumber(categoryCoverage?.copay_percent) ?? undefined,
    lineItems,
    isDental,
    estimated: result.decision === "MANUAL_REVIEW",
  };
}

export function buildClaimViewModel(
  result: ClaimProcessingResult,
  submission: ClaimSubmission,
): ClaimViewModel {
  const memberResolution = traceStep(result, "MEMBER_RESOLUTION");
  const memberDocumentConsistency = traceStep(result, "MEMBER_DOCUMENT_CONSISTENCY");
  const crossDocumentConsistency = traceStep(result, "CROSS_DOCUMENT_CONSISTENCY");
  const documentVerification = traceStep(result, "DOCUMENT_VERIFICATION");
  const documentExtraction = traceStep(result, "DOCUMENT_EXTRACTION");
  const policyEvaluation = traceStep(result, "POLICY_EVALUATION");
  const financialCalculation = traceStep(result, "FINANCIAL_CALCULATION");
  const fraudAnalysis = traceStep(result, "FRAUD_ANALYSIS");

  const input = inputFromTrace(result);
  const memberOutput = (memberResolution?.safe_output as Record<string, unknown>) || {};

  const memberId = String(submission.member_id || memberOutput.member_id || input.member_id || "Not available");
  const patientName = String(memberOutput.member_name || "Not available");
  const claimCategory = String(submission.claim_category || input.claim_category || "Not available");
  const treatmentDate = String(submission.treatment_date || input.treatment_date || "");
  const claimedAmount =
    toNumber(submission.claimed_amount) ??
    toNumber(input.claimed_amount) ??
    0;
  const policyId = String(
    submission.policy_id ||
      (policyEvaluation?.safe_output as Record<string, unknown> | undefined)?.policy_id ||
      input.policy_id ||
      "Not available",
  );
  const hospital = extractedHospital(documentExtraction) || "Not available";

  return {
    claimId: result.claim_id,
    patientName,
    memberId,
    claimCategory,
    claimCategoryLabel: formatCategoryLabel(claimCategory),
    treatmentDate,
    treatmentDateLabel: formatDisplayDate(treatmentDate),
    claimedAmount,
    policyId,
    hospital,
    financial: buildFinancialViewModel(result, submission, financialCalculation, policyEvaluation),
    memberResolution,
    memberDocumentConsistency,
    crossDocumentConsistency,
    documentVerification,
    documentExtraction,
    policyEvaluation,
    financialCalculation,
    fraudAnalysis,
  };
}

export function normalizeIdentityName(name: string): string {
  return name
    .normalize("NFKC")
    .replace(/^(mr|ms|mrs|dr)\.?\s*/i, "")
    .replace(/[^\w\s]/g, " ")
    .toLowerCase()
    .replace(/\s+/g, " ")
    .trim();
}

export function identityConsistencyLabel(check: { ok?: boolean; details?: Record<string, unknown> }): string {
  const names = Array.isArray(check.details?.found_names)
    ? check.details!.found_names.map(String)
    : [];
  const normalized = new Set(names.map(normalizeIdentityName).filter(Boolean));
  if (check.ok || (names.length > 0 && normalized.size <= 1)) {
    return "Identity matched";
  }
  return "Identity mismatch";
}

export function formatClaimAmount(amount: number): string {
  return formatCurrency(amount);
}
