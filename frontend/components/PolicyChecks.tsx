import { CheckCircle2, XCircle, ShieldCheck, ShieldAlert, ArrowRight } from "lucide-react";
import { cn } from "../app/utils";
import type { RuleResult, TraceEvent } from "../app/types";
import { identityConsistencyLabel } from "../app/claimViewModel";
import { useState } from "react";
import { Drawer } from "./Drawer";

function formatCheckName(name: string) {
  return name.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase());
}

export function PolicyChecks({ policyId, checks, extractedHospital, policyTrace }: { policyId: string; checks: RuleResult[]; extractedHospital?: string; policyTrace?: TraceEvent; }) {
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const failedChecks = checks.filter((c) => !c.ok);
  const isOk = failedChecks.length === 0;

  return (
    <div className="space-y-6">
      {!isOk && (
        <div className="bg-danger/5 border border-danger/20 p-4 rounded-xl flex items-start gap-3">
          <ShieldAlert className="w-5 h-5 text-danger shrink-0 mt-0.5" />
          <div>
            <h3 className="text-sm font-semibold text-danger">Policy Violation</h3>
            <p className="text-sm text-danger/80 mt-1">One or more policy rules were triggered.</p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {checks.map((check) => {
          const details = check.details || {};
          let detailText = "";
          
          if (check.name === "identity_consistency") {
            detailText = identityConsistencyLabel(check);
          } else if (check.name === "network_hospital") {
            const hospital = details.hospital || extractedHospital;
            detailText = hospital ? (details.is_network ? `${hospital} (Network)` : `${hospital} (Non-network)`) : "Not established";
          } else if (check.name === "category_coverage") {
            detailText = check.ok ? "Covered" : "Not covered";
          } else {
            detailText = check.ok ? "Passed" : "Failed";
          }

          return (
            <div key={check.name} className={cn("p-5 rounded-2xl border transition-colors shadow-sm", check.ok ? "bg-white border-plum-900/10 hover:border-plum-900/20" : "bg-danger/5 border-danger/20")}>
              <div className="flex items-start justify-between gap-4 mb-4">
                <div className={cn("p-2 rounded-xl", check.ok ? "bg-success/10 text-success" : "bg-danger/10 text-danger")}>
                  {check.ok ? <CheckCircle2 size={20} /> : <XCircle size={20} />}
                </div>
              </div>
              <h4 className="font-serif text-lg text-plum-900 mb-1">{formatCheckName(check.name)}</h4>
              <p className={cn("text-sm", check.ok ? "text-text-secondary" : "text-danger font-medium")}>{detailText}</p>
            </div>
          );
        })}
        
        {/* Trace View Card */}
        <div 
          onClick={() => setIsDrawerOpen(true)}
          className="p-5 rounded-2xl border border-plum-900/10 bg-cream-50 hover:bg-cream-100 hover:border-plum-900/30 transition-colors shadow-sm cursor-pointer group flex flex-col justify-between min-h-[140px]"
        >
          <div>
            <div className="p-2 rounded-xl bg-plum-900/5 text-plum-900 w-fit mb-4 group-hover:scale-110 transition-transform">
              <ShieldCheck size={20} />
            </div>
            <h4 className="font-serif text-lg text-plum-900 mb-1">View Details</h4>
            <p className="text-sm text-text-secondary">See exact policy terms</p>
          </div>
          <div className="flex justify-end">
            <ArrowRight size={20} className="text-plum-900/40 group-hover:text-plum-900 transition-colors transform group-hover:translate-x-1" />
          </div>
        </div>
      </div>

      <Drawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        title="Policy Evaluation Details"
        statusBadge={
          <span className={cn("px-2 py-0.5 rounded text-xs font-bold uppercase tracking-wider", isOk ? "bg-success/20 text-success" : "bg-danger/20 text-white")}>
            {isOk ? "All Passed" : "Violations Found"}
          </span>
        }
      >
        <div className="space-y-6">
          <div className="bg-cream-50 p-4 rounded-xl border border-plum-900/5">
            <p className="text-xs text-text-secondary uppercase tracking-wider mb-1">Policy ID</p>
            <p className="font-mono text-plum-900">{policyId}</p>
          </div>
          
          <div className="space-y-4">
            {checks.map(check => (
              <div key={check.name} className="border border-plum-900/10 rounded-xl p-4">
                <div className="flex items-center gap-2 mb-3">
                  {check.ok ? <CheckCircle2 className="text-success" size={18} /> : <XCircle className="text-danger" size={18} />}
                  <h4 className="font-medium text-plum-900">{formatCheckName(check.name)}</h4>
                </div>
                <div className="bg-cream-50 p-3 rounded-lg overflow-x-auto">
                  <pre className="text-xs font-mono text-text-secondary m-0">
                    {JSON.stringify(check.details, null, 2)}
                  </pre>
                </div>
              </div>
            ))}
          </div>
        </div>
      </Drawer>
    </div>
  );
}
