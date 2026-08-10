import { describe, expect, it } from "vitest";
import {
  buildClaimViewModel,
  identityConsistencyLabel,
  normalizeIdentityName,
} from "../app/claimViewModel";
import type { ClaimProcessingResult, ClaimSubmission } from "../app/types";

function mockResult(overrides: Partial<ClaimProcessingResult>): ClaimProcessingResult {
  return {
    claim_id: "CLM-test1234",
    processing_status: "COMPLETED",
    degraded: false,
    manual_review_recommended: false,
    component_failures: [],
    trace: [],
    ...overrides,
  };
}

function mockSubmission(overrides: Partial<ClaimSubmission> = {}): ClaimSubmission {
  return {
    member_id: "EMP002",
    policy_id: "PLUM_GHI_2024",
    claim_category: "DENTAL",
    treatment_date: "2024-10-15",
    claimed_amount: 12000,
    documents: [],
    ...overrides,
  };
}

describe("buildClaimViewModel", () => {
  it("derives overview fields from the current backend trace, not hardcoded defaults", () => {
    const submission = mockSubmission();
    const result = mockResult({
      decision: "PARTIAL",
      approved_amount: 8000,
      trace: [
        {
          trace_id: "1",
          step: "INPUT_VALIDATION",
          component: "ClaimIntake",
          status: "OK",
          safe_input: {
            member_id: "EMP002",
            policy_id: "PLUM_GHI_2024",
            claim_category: "DENTAL",
            treatment_date: "2024-10-15",
            claimed_amount: 12000,
          },
        },
        {
          trace_id: "2",
          step: "MEMBER_RESOLUTION",
          component: "MemberResolver",
          status: "OK",
          safe_output: {
            member_id: "EMP002",
            member_name: "Priya Singh",
          },
        },
        {
          trace_id: "3",
          step: "DOCUMENT_EXTRACTION",
          component: "DocumentExtractor",
          status: "OK",
          safe_output: [
            {
              file_id: "F011",
              document_type: "HOSPITAL_BILL",
              extracted: { hospital_name: "Smile Dental Clinic" },
            },
          ],
        },
        {
          trace_id: "4",
          step: "FINANCIAL_CALCULATION",
          component: "CalculationEngine",
          status: "OK",
          safe_output: {
            approved_amount: 8000,
            breakdown: {
              line_items: [
                {
                  description: "Root Canal Treatment",
                  claimed_amount: "8000",
                  eligible: true,
                  approved_amount: "8000",
                },
                {
                  description: "Teeth Whitening",
                  claimed_amount: "4000",
                  eligible: false,
                  approved_amount: "0",
                  reason: "Policy exclusion",
                },
              ],
            },
          },
        },
      ],
    });

    const viewModel = buildClaimViewModel(result, submission);
    expect(viewModel.patientName).toBe("Priya Singh");
    expect(viewModel.memberId).toBe("EMP002");
    expect(viewModel.claimCategoryLabel).toBe("Dental");
    expect(viewModel.treatmentDateLabel).toContain("2024");
    expect(viewModel.claimedAmount).toBe(12000);
    expect(viewModel.hospital).toBe("Smile Dental Clinic");
    expect(viewModel.financial?.claimed).toBe(12000);
    expect(viewModel.financial?.approved).toBe(8000);
    expect(viewModel.financial?.excluded).toBe(4000);
  });

  it("does not leak claim A overview into claim B", () => {
    const claimA = buildClaimViewModel(
      mockResult({
        claim_id: "CLM-aaaa",
        trace: [
          {
            trace_id: "1",
            step: "MEMBER_RESOLUTION",
            component: "MemberResolver",
            status: "OK",
            safe_output: { member_id: "EMP001", member_name: "Rajesh Kumar" },
          },
        ],
      }),
      mockSubmission({
        member_id: "EMP001",
        claim_category: "CONSULTATION",
        treatment_date: "2024-11-01",
        claimed_amount: 1500,
      }),
    );

    const claimB = buildClaimViewModel(
      mockResult({
        claim_id: "CLM-bbbb",
        trace: [
          {
            trace_id: "2",
            step: "MEMBER_RESOLUTION",
            component: "MemberResolver",
            status: "OK",
            safe_output: { member_id: "EMP005", member_name: "Vikram Joshi" },
          },
        ],
      }),
      mockSubmission({
        member_id: "EMP005",
        claim_category: "CONSULTATION",
        treatment_date: "2024-10-15",
        claimed_amount: 3000,
      }),
    );

    expect(claimA.patientName).toBe("Rajesh Kumar");
    expect(claimA.memberId).toBe("EMP001");
    expect(claimB.patientName).toBe("Vikram Joshi");
    expect(claimB.memberId).toBe("EMP005");
    expect(claimB.patientName).not.toBe(claimA.patientName);
    expect(claimB.memberId).not.toBe(claimA.memberId);
  });
});

describe("identityConsistencyLabel", () => {
  it("treats normalized OCR name variations as matched", () => {
    expect(normalizeIdentityName("Vikram Joshi")).toBe(normalizeIdentityName("VIKRAM JOSHI"));
    expect(
      identityConsistencyLabel({
        ok: false,
        details: { found_names: ["Vikram Joshi", "VIKRAM JOSHI"] },
      }),
    ).toBe("Identity matched");
  });
});
