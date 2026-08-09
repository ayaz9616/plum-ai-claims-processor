"use client";

import { useState } from "react";
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
import { ArrowLeft } from "lucide-react";

const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const STAGES_MAP: Record<string, number> = {
  RECEIVED: 0,
  VERIFICATION: 1,
  POLICY: 2,
  CALCULATION: 3,
  FRAUD: 4,
  APPROVED: 5,
  PARTIALLY_APPROVED: 5,
  REJECTED: 5,
  BLOCKED: 5,
  FAILED: 5,
};

export default function Page() {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState<ClaimProcessingResult | null>(null);
  const [lastSubmission, setLastSubmission] = useState<ClaimSubmission | null>(null);
  const [error, setError] = useState<string | null>(null);

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
    setError(null);
  };

  // Extract necessary details from the trace
  const docVerifyTrace = result?.trace.find(t => t.step === "DOCUMENT_VERIFICATION");
  const policyTrace = result?.trace.find(t => t.step === "POLICY_EVALUATION");
  const financeTrace = result?.trace.find(t => t.step === "FINANCIAL_CALCULATION");
  const fraudTrace = result?.trace.find(t => t.step === "FRAUD_ANALYSIS");
  const currentStageIndex = result ? STAGES_MAP[result.processing_status] ?? 5 : 0;

  const lineItems = financeTrace?.safe_output?.breakdown?.line_items || [];

  return (
    <main className="min-h-screen bg-slate-50/50 py-12 px-4 sm:px-6 lg:px-8 text-slate-900 font-sans">
      <div className="max-w-6xl mx-auto space-y-8">
        
        <header className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-slate-200 pb-6">
          <div>
            <div className="flex items-center gap-3">
              <div className="bg-blue-600 w-8 h-8 rounded-lg flex items-center justify-center text-white font-bold tracking-tighter">P</div>
              <h1 className="text-3xl font-bold tracking-tight text-slate-900">Plum Claims AI</h1>
            </div>
            <p className="mt-2 text-slate-500">Autonomous medical claims intake and adjudication.</p>
          </div>
          {result && (
            <button 
              onClick={handleReset}
              className="flex items-center gap-2 text-sm font-medium text-slate-600 bg-white border border-slate-200 px-4 py-2 rounded-lg hover:bg-slate-50 transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              New Claim
            </button>
          )}
        </header>

        {error && (
          <div className="bg-red-50 border-l-4 border-red-500 p-4 rounded-r-lg">
            <h3 className="text-red-800 font-medium">Error</h3>
            <p className="text-red-700 text-sm mt-1">{error}</p>
          </div>
        )}

        {!result ? (
          <div className="max-w-3xl mx-auto">
            <ClaimForm onSubmit={handleSubmitClaim} isLoading={isSubmitting} />
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            
            {/* Left Column - Main Dashboard */}
            <div className="lg:col-span-8 space-y-8">
              
              <ProcessingPipeline 
                currentStageIndex={currentStageIndex} 
                isError={result.processing_status === "FAILED" || result.processing_status === "BLOCKED" || result.processing_status === "REJECTED"} 
              />

              <FailedComponents failures={result.component_failures || []} />

              {/* Decision Card */}
              <DecisionCard 
                decision={result.decision}
                approvedAmount={result.approved_amount}
                confidenceScore={result.confidence_score}
                processingStatus={result.processing_status}
                degraded={result.degraded}
                manualReviewRecommended={result.manual_review_recommended}
              />

              {/* Policy Checks (if executed) */}
              {policyTrace?.safe_output && (
                <PolicyChecks 
                  policyId={policyTrace.safe_output.policy_id || "Unknown"}
                  checks={policyTrace.safe_output.checks || []}
                />
              )}

              {/* Document Checks (if executed) */}
              {docVerifyTrace?.safe_output && (
                <DocumentChecks 
                  status={docVerifyTrace.safe_output.status}
                  message={docVerifyTrace.safe_output.message}
                  required={docVerifyTrace.safe_output.required || []}
                  provided={docVerifyTrace.safe_output.provided || []}
                  missing={docVerifyTrace.safe_output.missing || []}
                  unreadable={docVerifyTrace.safe_output.unreadable || []}
                  wrongType={docVerifyTrace.safe_output.wrong_type || []}
                />
              )}

              {/* Financial Calculation (if executed) */}
              {financeTrace?.safe_output && financeTrace.safe_output.breakdown && (
                <>
                  <FinancialBreakdown 
                    claimed={financeTrace.safe_output.breakdown.claimed || "0"}
                    networkApplied={financeTrace.safe_output.breakdown.network_applied || false}
                    networkDiscount={financeTrace.safe_output.breakdown.network_discount || "0"}
                    copay={financeTrace.safe_output.breakdown.copay || "0"}
                    approved={financeTrace.safe_output.breakdown.approved || "0"}
                  />
                  <LineItemTable lineItems={lineItems} />
                </>
              )}

              {/* Fraud Analysis */}
              {fraudTrace && (
                <FraudAnalysisView 
                  ok={fraudTrace.safe_output?.ok ?? null}
                  manualReview={fraudTrace.safe_output?.manual_review ?? null}
                  signals={fraudTrace.safe_output?.signals || []}
                  degraded={fraudTrace.status === "DEGRADED"}
                />
              )}
              
              {lastSubmission && result && (
                <DownloadReportButton submission={lastSubmission} result={result} />
              )}
            </div>

            {/* Right Column - Audit Trace */}
            <div className="lg:col-span-4">
              <div className="sticky top-6">
                <AuditTimeline trace={result.trace} />
              </div>
            </div>
            
          </div>
        )}
      </div>
    </main>
  );
}
