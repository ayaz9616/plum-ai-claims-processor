import { Shield, ShieldAlert, AlertTriangle, ShieldCheck, Info } from "lucide-react";
import { cn } from "../app/utils";
import type { TraceEvent } from "../app/types";

interface FraudAnalysisProps {
  ok: boolean | null;
  manualReview: boolean | null;
  signals: Array<{
    type: string;
    component?: string;
    [key: string]: any;
  }>;
  degraded?: boolean;
  fraudTrace?: TraceEvent;
}

export function FraudAnalysisView({ ok, manualReview, signals, degraded, fraudTrace }: FraudAnalysisProps) {
  const isFailedComponent = degraded || ok === null;
  const hasSignals = signals && signals.length > 0;

  const output = fraudTrace?.safe_output || {};
  const riskLevelRaw = output.risk_level || (isFailedComponent ? "DEGRADED" : (!ok || manualReview) ? "HIGH" : "LOW");
  const riskLevel = riskLevelRaw.toLowerCase();
  
  const fraudScore = output.fraud_score !== undefined ? output.fraud_score : null;
  const checks = output.checks || {};
  const explanation = output.explanation || "";

  return (
    <div className={cn(
      "rounded-2xl border p-6 md:p-8 shadow-soft transition-colors",
      riskLevel === "low" ? "bg-white border-plum-900/5" :
      riskLevel === "degraded" ? "bg-warning/5 border-warning/20" :
      "bg-danger/5 border-danger/20"
    )}>
      <div className="flex items-start gap-4 mb-6">
        <div className={cn(
          "p-3 rounded-xl flex-shrink-0",
          riskLevel === "low" ? "bg-success/10 text-success" :
          riskLevel === "degraded" ? "bg-warning/10 text-warning" :
          "bg-danger/10 text-danger"
        )}>
          {riskLevel === "low" ? <ShieldCheck size={28} /> : 
           riskLevel === "degraded" ? <AlertTriangle size={28} /> : 
           <ShieldAlert size={28} />}
        </div>
        <div className="flex-1">
          <div className="flex justify-between items-start">
            <div>
              <h3 className="font-serif text-2xl text-plum-900">
                {riskLevel === "low" ? "No Fraud Signals" :
                 riskLevel === "degraded" ? "Degraded Analysis" :
                 "Fraud Signals Detected"}
              </h3>
              <div className="flex items-center gap-2 mt-2">
                <span className={cn(
                  "text-xs font-bold px-2 py-0.5 rounded-full uppercase tracking-wider",
                  riskLevel === "low" ? "bg-success/10 text-success" :
                  riskLevel === "degraded" ? "bg-warning/10 text-warning" :
                  "bg-danger/10 text-danger"
                )}>
                  {riskLevelRaw} RISK
                </span>
                {manualReview && (
                  <span className="text-xs font-bold px-2 py-0.5 rounded-full uppercase tracking-wider bg-warning/20 text-warning-dark">
                    MANUAL REVIEW
                  </span>
                )}
              </div>
            </div>
            {fraudScore !== null && (
              <div className="text-right">
                <div className="text-3xl font-serif font-medium text-plum-900">
                  {fraudScore.toFixed(2)}
                </div>
                <div className="text-[10px] font-bold text-plum-900/40 uppercase tracking-widest mt-1">
                  Fraud Score
                </div>
              </div>
            )}
          </div>
          
          <p className="text-sm text-text-secondary mt-3 leading-relaxed">
            {isFailedComponent
              ? (explanation || "Analysis degraded or component failed — manual review recommended")
              : (explanation || (ok ? "All fraud checks passed with no anomalies" : "Unusual activity requires further investigation"))}
          </p>
        </div>
      </div>

      {isFailedComponent && (
        <div className="mb-6 p-4 rounded-xl bg-warning/10 border border-warning/20 text-warning flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
          <div>
            <span className="font-medium text-sm">Component Warning</span>
            <p className="text-sm mt-0.5 text-warning/80">
              {explanation || "Fraud analysis was skipped or degraded."}
            </p>
          </div>
        </div>
      )}

      {!isFailedComponent && Object.keys(checks).length === 0 && !hasSignals && (
        <div className="flex items-center gap-2 text-success bg-success/5 p-4 rounded-xl border border-success/10">
          <Shield size={18} />
          <p className="text-sm font-medium">All checks passed. No signals found.</p>
        </div>
      )}

      {Object.keys(checks).length > 0 && (
        <div className="space-y-3 mt-6">
          <h4 className="text-xs font-bold text-plum-900/50 uppercase tracking-wider mb-2">Detailed Checks</h4>
          
          {/* Same Day Claims */}
          {checks.same_day_claims && (
            <div className={cn(
              "flex items-start justify-between p-4 rounded-xl border",
              checks.same_day_claims.status === "FAILED" ? "bg-danger/5 border-danger/20" : "bg-white border-plum-900/10"
            )}>
              <div>
                <p className={cn("text-sm font-semibold", checks.same_day_claims.status === "FAILED" ? "text-danger" : "text-plum-900")}>
                  Same-Day Claims
                </p>
                <p className="text-xs text-text-secondary mt-1">
                  {checks.same_day_claims.count} prior claims
                </p>
              </div>
              <div className="text-right">
                <span className={cn(
                  "text-xs font-medium",
                  checks.same_day_claims.status === "FAILED" ? "text-danger" : "text-success"
                )}>
                  {checks.same_day_claims.status === "FAILED" ? "⚠ Manual Review Trigger" : "✓ Within Limit"}
                </span>
                <p className="text-xs text-text-secondary mt-1">Limit: {checks.same_day_claims.threshold}</p>
              </div>
            </div>
          )}

          {/* Monthly Claims */}
          {checks.monthly_claims && (
            <div className={cn(
              "flex items-start justify-between p-4 rounded-xl border",
              checks.monthly_claims.status === "FAILED" ? "bg-danger/5 border-danger/20" : "bg-white border-plum-900/10"
            )}>
              <div>
                <p className={cn("text-sm font-semibold", checks.monthly_claims.status === "FAILED" ? "text-danger" : "text-plum-900")}>
                  Monthly Claims
                </p>
                <p className="text-xs text-text-secondary mt-1">
                  {checks.monthly_claims.count} prior claims
                </p>
              </div>
              <div className="text-right">
                <span className={cn(
                  "text-xs font-medium",
                  checks.monthly_claims.status === "FAILED" ? "text-danger" : "text-success"
                )}>
                  {checks.monthly_claims.status === "FAILED" ? "⚠ Manual Review Trigger" : "✓ Within Limit"}
                </span>
                <p className="text-xs text-text-secondary mt-1">Limit: {checks.monthly_claims.threshold}</p>
              </div>
            </div>
          )}

          {/* High Value Claim */}
          {checks.high_value_claim && (
            <div className={cn(
              "flex items-start justify-between p-4 rounded-xl border",
              checks.high_value_claim.status === "FAILED" ? "bg-danger/5 border-danger/20" : "bg-white border-plum-900/10"
            )}>
              <div>
                <p className={cn("text-sm font-semibold", checks.high_value_claim.status === "FAILED" ? "text-danger" : "text-plum-900")}>
                  High-Value Claim
                </p>
                <p className="text-xs text-text-secondary mt-1">
                  ₹{checks.high_value_claim.amount.toLocaleString('en-IN')}
                </p>
              </div>
              <div className="text-right">
                <span className={cn(
                  "text-xs font-medium",
                  checks.high_value_claim.status === "FAILED" ? "text-danger" : "text-success"
                )}>
                  {checks.high_value_claim.status === "FAILED" ? "⚠ Trigger" : "✓ Normal"}
                </span>
                <p className="text-xs text-text-secondary mt-1">
                  Threshold: ₹{checks.high_value_claim.threshold.toLocaleString('en-IN')}
                </p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Fallback for legacy signals if checks are not present */}
      {Object.keys(checks).length === 0 && hasSignals && (
        <div className="space-y-3 mt-6">
          <h4 className="text-xs font-bold text-plum-900/50 uppercase tracking-wider mb-2">Signals</h4>
          {signals.map((signal, idx) => (
            <div key={idx} className={cn(
              "flex items-start gap-3 p-4 rounded-xl border",
              isFailedComponent ? "bg-warning/5 border-warning/10" : "bg-danger/5 border-danger/10"
            )}>
              <AlertTriangle className={cn("w-5 h-5 shrink-0 mt-0.5", isFailedComponent ? "text-warning" : "text-danger")} />
              <div className="flex-1">
                <p className={cn("text-sm font-medium", isFailedComponent ? "text-warning" : "text-danger")}>
                  {signal.type.replace(/_/g, " ").replace(/\b\w/g, (l: string) => l.toUpperCase())}
                </p>
                <div className="mt-2 bg-white/50 p-3 rounded-lg overflow-x-auto">
                  <pre className="text-xs font-mono text-text-secondary m-0 whitespace-pre-wrap">
                    {JSON.stringify(signal, null, 2)}
                  </pre>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
