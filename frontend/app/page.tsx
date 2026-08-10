"use client";

import { useMemo, useState } from "react";
import { ClaimForm } from "../components/ClaimForm";
import { DecisionCard } from "../components/DecisionCard";
import { DocumentChecks } from "../components/DocumentChecks";
import { PolicyChecks } from "../components/PolicyChecks";
import { FinancialBreakdown } from "../components/FinancialBreakdown";
import { FraudAnalysisView } from "../components/FraudAnalysisView";
import { AuditTimeline } from "../components/AuditTimeline";
import { ProcessingPipeline } from "../components/ProcessingPipeline";
import { LineItemTable } from "../components/LineItemTable";
import { FailedComponents } from "../components/FailedComponents";
import { DownloadReportButton } from "../components/DownloadReportButton";
import type { ClaimSubmission, ClaimProcessingResult } from "./types";
import { buildClaimViewModel, formatClaimAmount } from "./claimViewModel";
import { Loader2, Plus } from "lucide-react";

const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const STAGES_MAP: Record<string, number> = {
  RECEIVED: 0,
  DOCUMENTS: 1,
  VERIFICATION: 2,
  POLICY: 3,
  CALCULATION: 4,
  FRAUD: 5,
  APPROVED: 6,
  PARTIALLY_APPROVED: 6,
  REJECTED: 6,
  BLOCKED: 6,
  BLOCKED_DOCUMENT: 6,
  FAILED: 6,
  COMPLETED: 6,
  PENDING_MANUAL_REVIEW: 6,
};

export default function Page() {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState<ClaimProcessingResult | null>(null);
  const [lastSubmission, setLastSubmission] = useState<ClaimSubmission | null>(null);
  const [error, setError] = useState<string | null>(null);

  const viewModel = useMemo(() => {
    if (!result || !lastSubmission) return null;
    return buildClaimViewModel(result, lastSubmission);
  }, [result, lastSubmission]);

  const handleSubmitClaim = async (submission: ClaimSubmission) => {
    setIsSubmitting(true);
    setError(null);
    setResult(null);
    setLastSubmission(submission);

    try {
      const response = await fetch(`${apiUrl}/api/claims/process`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(submission),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Claim processing failed");
      }

      setResult(data as ClaimProcessingResult);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An unexpected error occurred.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReset = () => {
    setResult(null);
    setLastSubmission(null);
    setError(null);
    setIsSubmitting(false);
  };

  const currentStageIndex = result ? STAGES_MAP[result.processing_status] ?? 5 : 0;
  const docVerifyTrace = viewModel?.documentVerification;
  const policyTrace = viewModel?.policyEvaluation;
  const financeTrace = viewModel?.financialCalculation;
  const fraudTrace = viewModel?.fraudAnalysis;
  const extractionTrace = viewModel?.documentExtraction;
  const financial = viewModel?.financial;
  const lineItems = financial?.lineItems || [];

  return (
    <main className="min-h-screen bg-cream-50 text-text-primary font-sans">
      <header className="bg-plum-900 text-cream-50 border-b border-plum-800">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded bg-coral-500 flex items-center justify-center font-serif text-xl font-bold tracking-tighter text-plum-900">
                p
              </div>
              <div className="flex flex-col">
                <span className="font-serif text-xl leading-none">plum Claims AI</span>
                <span className="text-[10px] text-coral-400 uppercase tracking-widest mt-0.5">Operations Platform</span>
              </div>
            </div>

            <nav className="hidden md:flex items-center gap-6 ml-8 text-sm text-cream-100/70">
              <span className="text-coral-500 font-medium">Claims</span>
              <span className="hover:text-cream-100 transition-colors cursor-pointer">Analytics</span>
              <span className="hover:text-cream-100 transition-colors cursor-pointer">Settings</span>
            </nav>
          </div>

          <div className="flex items-center gap-4">
            {result && viewModel && (
              <span className="text-sm font-medium text-cream-100/70 hidden sm:inline-block">
                Claim {viewModel.claimId}
              </span>
            )}
            <button
              onClick={handleReset}
              className="flex items-center gap-2 text-sm font-medium text-plum-900 bg-coral-500 hover:bg-coral-400 px-4 py-2 rounded-full transition-colors"
            >
              <Plus size={16} />
              New Claim
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-12">
        {error && (
          <div className="bg-red-50 border border-danger/20 p-4 rounded-xl flex flex-col gap-2">
            <h3 className="text-danger font-serif text-lg">Error</h3>
            <p className="text-danger/80 text-sm">{error}</p>
          </div>
        )}

        {isSubmitting ? (
          <div className="max-w-3xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="bg-white rounded-[24px] shadow-elevated border border-plum-900/5 p-12 text-center">
              <Loader2 className="w-10 h-10 text-coral-500 animate-spin mx-auto mb-4" />
              <h2 className="font-serif text-2xl text-plum-900 mb-2">Processing new claim...</h2>
              <p className="text-text-secondary">
                Validating documents, evaluating policy rules, and calculating the outcome.
              </p>
            </div>
          </div>
        ) : !result || !viewModel ? (
          <div className="max-w-3xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-500">
            <ClaimForm onSubmit={handleSubmitClaim} isLoading={isSubmitting} />
          </div>
        ) : (
          <div key={viewModel.claimId} className="space-y-12 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="mb-8">
              <ProcessingPipeline
                currentStageIndex={currentStageIndex}
                isError={
                  result.processing_status === "FAILED" ||
                  result.processing_status === "BLOCKED" ||
                  result.processing_status === "REJECTED"
                }
              />
            </div>

            <FailedComponents failures={result.component_failures || []} />

            <DecisionCard
              decision={result.decision}
              approvedAmount={result.approved_amount}
              reimbursableAmount={result.reimbursable_amount}
              confidenceScore={result.confidence_score}
              processingStatus={result.processing_status}
              degraded={result.degraded}
              manualReviewRecommended={result.manual_review_recommended}
              decisionSummary={result.decision_summary}
              trace={result.trace}
            />

            <section className="bg-white rounded-2xl shadow-soft border border-plum-900/5 p-6 md:p-8">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <div className="text-[11px] font-bold tracking-widest text-plum-900/40 uppercase mb-1">Claim Overview</div>
                  <h2 className="font-serif text-2xl text-plum-900">Everything you need to know</h2>
                </div>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-6 md:gap-8">
                <div>
                  <div className="text-xs text-text-secondary mb-1">Patient</div>
                  <div className="font-medium text-text-primary">{viewModel.patientName}</div>
                  <div className="text-xs text-text-secondary mt-0.5">{viewModel.memberId}</div>
                </div>
                <div>
                  <div className="text-xs text-text-secondary mb-1">Claim Type</div>
                  <div className="font-medium text-text-primary">{viewModel.claimCategoryLabel}</div>
                </div>
                <div>
                  <div className="text-xs text-text-secondary mb-1">Treatment Date</div>
                  <div className="font-medium text-text-primary">{viewModel.treatmentDateLabel}</div>
                </div>
                <div>
                  <div className="text-xs text-text-secondary mb-1">Claimed Amount</div>
                  <div className="font-medium text-text-primary">{formatClaimAmount(viewModel.claimedAmount)}</div>
                </div>
                <div>
                  <div className="text-xs text-text-secondary mb-1">Policy</div>
                  <div className="font-medium text-text-primary">{viewModel.policyId}</div>
                </div>
                <div className="col-span-2">
                  <div className="text-xs text-text-secondary mb-1">Hospital</div>
                  <div className="font-medium text-text-primary">{viewModel.hospital}</div>
                </div>
              </div>
            </section>

            {docVerifyTrace?.safe_output && (
              <section>
                <div className="mb-6">
                  <div className="text-[11px] font-bold tracking-widest text-plum-900/40 uppercase mb-1">Documents</div>
                  <h2 className="font-serif text-2xl text-plum-900">Evidence verified</h2>
                </div>
                <DocumentChecks
                  status={docVerifyTrace.safe_output.status}
                  message={docVerifyTrace.safe_output.message}
                  required={docVerifyTrace.safe_output.required || []}
                  provided={docVerifyTrace.safe_output.provided || []}
                  missing={docVerifyTrace.safe_output.missing || []}
                  unreadable={docVerifyTrace.safe_output.unreadable || []}
                  wrongType={docVerifyTrace.safe_output.wrong_type || []}
                  extractionTrace={extractionTrace}
                />
              </section>
            )}

            {policyTrace?.safe_output && (
              <section>
                <div className="mb-6">
                  <div className="text-[11px] font-bold tracking-widest text-plum-900/40 uppercase mb-1">Policy Evaluation</div>
                  <h2 className="font-serif text-2xl text-plum-900">Coverage looks good.</h2>
                </div>
                <PolicyChecks
                  policyId={policyTrace.safe_output.policy_id || viewModel.policyId}
                  checks={policyTrace.safe_output.checks || []}
                  extractedHospital={viewModel.hospital !== "Not available" ? viewModel.hospital : undefined}
                  policyTrace={policyTrace}
                />
              </section>
            )}

            {financial && (
              <section>
                <div className="mb-6">
                  <div className="text-[11px] font-bold tracking-widest text-plum-900/40 uppercase mb-1">Financial Breakdown</div>
                  <h2 className="font-serif text-2xl text-plum-900">Calculation summary</h2>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <FinancialBreakdown
                    claimed={financial.claimed}
                    networkApplied={financial.networkApplied}
                    networkDiscount={financial.networkDiscount}
                    copay={financial.copay}
                    approved={financial.approved}
                    excluded={financial.excluded}
                    copayPercent={financial.copayPercent}
                    estimated={financial.estimated}
                    isDental={financial.isDental}
                    financeTrace={financeTrace}
                  />
                  {lineItems.length > 0 && (
                    <div className="bg-white rounded-2xl shadow-soft border border-plum-900/5 p-6 flex flex-col justify-center">
                      <LineItemTable lineItems={lineItems as Parameters<typeof LineItemTable>[0]["lineItems"]} />
                    </div>
                  )}
                </div>
              </section>
            )}

            {fraudTrace && (
              <section>
                <div className="mb-6">
                  <div className="text-[11px] font-bold tracking-widest text-plum-900/40 uppercase mb-1">Fraud Analysis</div>
                  <h2 className="font-serif text-2xl text-plum-900">Risk assessment</h2>
                </div>
                <FraudAnalysisView
                  ok={fraudTrace.safe_output?.ok ?? null}
                  manualReview={fraudTrace.safe_output?.manual_review ?? null}
                  signals={fraudTrace.safe_output?.signals || []}
                  degraded={fraudTrace.status === "DEGRADED"}
                  fraudTrace={fraudTrace}
                />
              </section>
            )}

            <section>
              <AuditTimeline trace={result.trace} />
            </section>

            {lastSubmission && result && (
              <div className="pt-8 border-t border-plum-900/10 flex justify-center">
                <DownloadReportButton submission={lastSubmission} result={result} />
              </div>
            )}
          </div>
        )}
      </div>
    </main>
  );
}
