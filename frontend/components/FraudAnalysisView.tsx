import { Shield, ShieldAlert, AlertTriangle } from "lucide-react";
import { cn } from "../app/utils";

interface FraudAnalysisProps {
  ok: boolean | null;
  manualReview: boolean | null;
  signals: Array<{
    type: string;
    component?: string;
    [key: string]: any;
  }>;
  degraded?: boolean;
}

export function FraudAnalysisView({ ok, manualReview, signals, degraded }: FraudAnalysisProps) {
  const isFailedComponent = degraded || ok === null;
  const hasSignals = signals && signals.length > 0;
  
  return (
    <div className="rounded-xl border border-slate-200 bg-white overflow-hidden shadow-sm">
      <div className={cn("px-6 py-4 border-b flex items-center gap-3", 
        isFailedComponent ? "bg-amber-50" : (ok ? "bg-emerald-50" : "bg-red-50")
      )}>
        {isFailedComponent ? (
          <AlertTriangle className="w-5 h-5 text-amber-600" />
        ) : ok ? (
          <Shield className="w-5 h-5 text-emerald-600" />
        ) : (
          <ShieldAlert className="w-5 h-5 text-red-600" />
        )}
        <div>
          <h3 className="text-lg font-semibold text-slate-800">Fraud Analysis</h3>
          <p className="text-sm text-slate-500">
            {isFailedComponent 
              ? "Analysis degraded or component failed" 
              : (ok ? "No critical fraud signals detected" : "Fraud signals detected")}
          </p>
        </div>
      </div>

      <div className="p-6">
        {isFailedComponent && (
          <div className="mb-4 p-4 rounded-lg bg-amber-100 border border-amber-200 text-amber-800 text-sm">
            <span className="font-semibold">Simulated Failure: </span>
            Fraud analysis was skipped due to a simulated component failure. Graceful degradation applied.
          </div>
        )}

        {!isFailedComponent && !hasSignals && (
          <p className="text-sm text-slate-600">All checks passed. No signals found.</p>
        )}

        {hasSignals && (
          <ul className="space-y-3">
            {signals.map((signal, idx) => (
              <li key={idx} className="flex items-start gap-3 p-3 rounded-lg border border-slate-200 bg-slate-50">
                <AlertTriangle className={cn("w-5 h-5 shrink-0 mt-0.5", isFailedComponent ? "text-amber-500" : "text-red-500")} />
                <div>
                  <p className="text-sm font-medium text-slate-800">
                    Type: {signal.type.replace(/_/g, " ")}
                  </p>
                  <p className="text-xs text-slate-500 mt-1">
                    {JSON.stringify(signal, null, 2)}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
