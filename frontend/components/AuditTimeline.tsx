import { useState } from "react";
import { Activity, CheckCircle2, AlertTriangle, AlertOctagon, Circle, ChevronDown, ChevronRight } from "lucide-react";
import { cn } from "../app/utils";
import type { TraceEvent } from "../app/types";

export function AuditTimeline({ trace }: { trace: TraceEvent[] }) {
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);

  if (!trace || trace.length === 0) return null;

  const toggleExpand = (index: number) => {
    setExpandedIndex(expandedIndex === index ? null : index);
  };

  return (
    <div>
      <div className="mb-6">
        <div className="text-[11px] font-bold tracking-widest text-plum-900/40 uppercase mb-1">Audit Trail</div>
        <h2 className="font-serif text-2xl text-plum-900">Processing trace</h2>
      </div>

      <div className="space-y-3">
        {trace.map((event, index) => {
          const isDegraded = event.status === "DEGRADED";
          const isError = event.status === "ERROR" || event.status === "BLOCKED" || event.status === "FAILED";
          const isReview = event.status === "REVIEW_REQUIRED" || event.status === "DEGRADED";
          const isOk = event.status === "OK" || event.status === "PASSED";
          const isExpanded = expandedIndex === index;

          return (
            <div key={event.trace_id || index} className="bg-white rounded-xl border border-plum-900/5 shadow-sm overflow-hidden">
              <button 
                onClick={() => toggleExpand(index)}
                className="w-full flex items-center gap-4 p-4 hover:bg-cream-50 transition-colors text-left"
              >
                <div className={cn(
                  "w-8 h-8 rounded-full flex items-center justify-center shrink-0",
                  isOk ? "bg-success/10 text-success" :
                  (isDegraded || isReview) ? "bg-warning/10 text-warning" :
                  isError ? "bg-danger/10 text-danger" :
                  "bg-plum-900/5 text-text-secondary"
                )}>
                  {isOk && <CheckCircle2 size={16} />}
                  {(isDegraded || isReview) && <AlertTriangle size={16} />}
                  {isError && <AlertOctagon size={16} />}
                  {!isOk && !isError && !isDegraded && !isReview && <Circle size={16} />}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h4 className="text-sm font-medium text-plum-900 truncate">
                      {event.step.replace(/_/g, " ")}
                    </h4>
                    <span className={cn(
                      "text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider shrink-0",
                      isOk ? "bg-success/10 text-success" :
                      (isDegraded || isReview) ? "bg-warning/10 text-warning" :
                      isError ? "bg-danger/10 text-danger" :
                      "bg-plum-900/5 text-text-secondary"
                    )}>
                      {event.status}
                    </span>
                  </div>
                  {event.summary && (
                    <p className="text-xs text-text-secondary mt-0.5 truncate">{event.summary}</p>
                  )}
                </div>

                <div className="text-plum-900/30 shrink-0">
                  {isExpanded ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                </div>
              </button>

              {isExpanded && (
                <div className="px-4 pb-4 border-t border-plum-900/5">
                  <div className="pt-4 space-y-4">
                    {event.summary && (
                      <div>
                        <p className="text-xs text-text-secondary uppercase tracking-wider mb-1">Summary</p>
                        <p className="text-sm text-plum-900">{event.summary}</p>
                      </div>
                    )}
                    
                    {event.error && (
                      <div className="p-3 rounded-xl bg-danger/5 border border-danger/10">
                        <p className="text-xs text-danger uppercase tracking-wider mb-1 font-bold">Error</p>
                        <p className="text-sm text-danger">{event.error}</p>
                      </div>
                    )}

                    {event.reason_code && (
                      <div>
                        <p className="text-xs text-text-secondary uppercase tracking-wider mb-1">Reason Code</p>
                        <span className="text-xs font-mono bg-plum-900/5 text-plum-900 px-2 py-1 rounded">{event.reason_code}</span>
                      </div>
                    )}

                    {(event.safe_output || event.evidence) && (
                      <div>
                        <p className="text-xs text-text-secondary uppercase tracking-wider mb-2">Evidence / Output</p>
                        <div className="bg-cream-50 p-3 rounded-xl overflow-x-auto border border-plum-900/5">
                          <pre className="text-xs font-mono text-text-secondary m-0 whitespace-pre-wrap max-h-64 overflow-y-auto">
                            {JSON.stringify(event.safe_output || event.evidence, null, 2)}
                          </pre>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

