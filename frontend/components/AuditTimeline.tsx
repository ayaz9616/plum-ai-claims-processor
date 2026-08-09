import { Activity, CheckCircle2, AlertTriangle, AlertOctagon } from "lucide-react";
import { cn } from "../app/utils";
import type { TraceEvent } from "../app/types";

export function AuditTimeline({ trace }: { trace: TraceEvent[] }) {
  if (!trace || trace.length === 0) return null;

  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
      <div className="px-6 py-4 border-b bg-slate-50 flex items-center gap-3">
        <Activity className="w-5 h-5 text-slate-600" />
        <div>
          <h3 className="text-lg font-semibold text-slate-800">Audit Trace Timeline</h3>
          <p className="text-sm text-slate-500">Chronological system execution log</p>
        </div>
      </div>

      <div className="p-6">
        <div className="relative border-l border-slate-200 ml-3 space-y-6">
          {trace.map((event, index) => {
            const isDegraded = event.status === "DEGRADED";
            const isError = event.status === "ERROR" || event.status === "BLOCKED" || event.status === "FAILED";
            const isOk = event.status === "OK" || event.status === "PASSED";

            return (
              <div key={event.trace_id || index} className="relative pl-6">
                <div className={cn(
                  "absolute -left-3 top-0.5 w-6 h-6 rounded-full border-2 bg-white flex items-center justify-center shadow-sm",
                  isOk ? "border-emerald-500" : isDegraded ? "border-amber-500" : "border-rose-500"
                )}>
                  {isOk && <CheckCircle2 className="w-3 h-3 text-emerald-500" />}
                  {isDegraded && <AlertTriangle className="w-3 h-3 text-amber-500" />}
                  {isError && <AlertOctagon className="w-3 h-3 text-rose-500" />}
                </div>

                <div>
                  <div className="flex items-baseline gap-2">
                    <h4 className="text-sm font-bold text-slate-900">{event.step}</h4>
                    <span className="text-xs font-medium text-slate-500">{event.component}</span>
                    <span className={cn(
                      "text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider ml-auto",
                      isOk ? "bg-emerald-100 text-emerald-700" : isDegraded ? "bg-amber-100 text-amber-700" : "bg-rose-100 text-rose-700"
                    )}>
                      {event.status}
                    </span>
                  </div>

                  {event.duration_ms !== undefined && (
                    <p className="text-xs text-slate-400 mt-1">Duration: {event.duration_ms}ms</p>
                  )}

                  {event.error && (
                    <div className="mt-2 text-sm text-amber-800 bg-amber-50 border border-amber-200 p-3 rounded-md">
                      <span className="font-semibold">Reason/Error:</span> {event.error}
                    </div>
                  )}
                  {event.summary && <p className="mt-2 text-sm text-slate-700">{event.summary}</p>}
                  {event.reason_code && <p className="mt-1 text-xs font-semibold text-rose-700">Reason: {event.reason_code}</p>}
                  {event.evidence && <details className="mt-2 text-xs text-slate-600"><summary className="cursor-pointer font-medium">Evidence</summary><pre className="mt-1 whitespace-pre-wrap bg-slate-50 p-2 rounded">{JSON.stringify(event.evidence, null, 2)}</pre></details>}

                  {event.safe_output && Object.keys(event.safe_output).length > 0 && !isDegraded && !isError && (
                    <div className="mt-2 text-xs font-mono text-slate-600 bg-slate-50 border border-slate-100 p-2 rounded-md max-h-32 overflow-y-auto">
                      {JSON.stringify(event.safe_output, null, 2)}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
