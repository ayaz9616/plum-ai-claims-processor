import { Check, X, ShieldAlert, ShieldCheck } from "lucide-react";
import { cn } from "../app/utils";
import type { RuleResult } from "../app/types";

export function PolicyChecks({ policyId, checks }: { policyId: string; checks: RuleResult[] }) {
  const failedChecks = checks.filter((c) => !c.ok);
  const isOk = failedChecks.length === 0;

  return (
    <div className="rounded-xl border border-slate-200 bg-white overflow-hidden shadow-sm">
      <div className={cn("px-6 py-4 border-b flex items-center gap-3", isOk ? "bg-slate-50" : "bg-amber-50")}>
        {isOk ? <ShieldCheck className="w-5 h-5 text-emerald-600" /> : <ShieldAlert className="w-5 h-5 text-amber-600" />}
        <div>
          <h3 className="text-lg font-semibold text-slate-800">Policy Evaluation</h3>
          <p className="text-sm text-slate-500">Evaluated against {policyId}</p>
        </div>
      </div>

      <div className="p-0 max-h-96 overflow-y-auto">
        <ul className="divide-y divide-slate-100">
          {checks.map((check) => (
            <li key={check.name} className="flex items-start gap-4 p-4 hover:bg-slate-50 transition-colors">
              <div className="mt-0.5 shrink-0">
                {check.ok ? (
                  <Check className="w-5 h-5 text-emerald-500" />
                ) : (
                  <X className="w-5 h-5 text-rose-500" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <p className={cn("text-sm font-medium", check.ok ? "text-slate-700" : "text-rose-700")}>
                  {check.name.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase())}
                </p>
                {check.details && Object.keys(check.details).length > 0 && (
                  <div className="mt-1 bg-slate-100 p-2 rounded-md text-xs font-mono text-slate-600 break-words whitespace-pre-wrap">
                    {JSON.stringify(check.details, null, 2)}
                  </div>
                )}
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
