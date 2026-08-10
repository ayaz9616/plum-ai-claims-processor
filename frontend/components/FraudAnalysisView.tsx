import { Shield, ShieldAlert, AlertTriangle, ShieldCheck } from "lucide-react";
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

  const riskLevel = isFailedComponent ? "degraded" : (!ok || manualReview) ? "high" : "low";
  
  return (
    <div className={cn(
      "rounded-2xl border p-6 md:p-8 shadow-soft transition-colors",
      riskLevel === "low" ? "bg-white border-plum-900/5" :
      riskLevel === "degraded" ? "bg-warning/5 border-warning/20" :
      "bg-danger/5 border-danger/20"
    )}>
      <div className="flex items-start gap-4 mb-6">
        <div className={cn(
          "p-3 rounded-xl",
          riskLevel === "low" ? "bg-success/10 text-success" :
          riskLevel === "degraded" ? "bg-warning/10 text-warning" :
          "bg-danger/10 text-danger"
        )}>
          {riskLevel === "low" ? <ShieldCheck size={28} /> : 
           riskLevel === "degraded" ? <AlertTriangle size={28} /> : 
           <ShieldAlert size={28} />}
        </div>
        <div>
          <h3 className="font-serif text-2xl text-plum-900">
            {riskLevel === "low" ? "No Fraud Signals" :
             riskLevel === "degraded" ? "Degraded Analysis" :
             "Fraud Signals Detected"}
          </h3>
          <p className="text-sm text-text-secondary mt-1">
            {isFailedComponent
              ? "Analysis degraded or component failed — manual review recommended"
              : ok ? "All fraud checks passed with no anomalies" : "Unusual activity requires further investigation"}
          </p>
        </div>
      </div>

      {isFailedComponent && (
        <div className="mb-6 p-4 rounded-xl bg-warning/10 border border-warning/20 text-warning flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
          <div>
            <span className="font-medium text-sm">Simulated Failure</span>
            <p className="text-sm mt-0.5 text-warning/80">
              Fraud analysis was skipped due to a simulated component failure. Graceful degradation applied.
            </p>
          </div>
        </div>
      )}

      {!isFailedComponent && !hasSignals && (
        <div className="flex items-center gap-2 text-success bg-success/5 p-4 rounded-xl border border-success/10">
          <Shield size={18} />
          <p className="text-sm font-medium">All checks passed. No signals found.</p>
        </div>
      )}

      {hasSignals && (
        <div className="space-y-3">
          {signals.map((signal, idx) => (
            <div key={idx} className={cn(
              "flex items-start gap-3 p-4 rounded-xl border",
              isFailedComponent ? "bg-warning/5 border-warning/10" : "bg-danger/5 border-danger/10"
            )}>
              <AlertTriangle className={cn("w-5 h-5 shrink-0 mt-0.5", isFailedComponent ? "text-warning" : "text-danger")} />
              <div className="flex-1">
                <p className={cn("text-sm font-medium", isFailedComponent ? "text-warning" : "text-danger")}>
                  {signal.type.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase())}
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

