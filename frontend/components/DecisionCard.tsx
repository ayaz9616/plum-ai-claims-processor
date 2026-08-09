import { CheckCircle2, XCircle, AlertTriangle, Info, Clock, AlertOctagon } from "lucide-react";
import { cn } from "../app/utils";

interface DecisionCardProps {
  decision?: string;
  approvedAmount?: number;
  confidenceScore?: number;
  processingStatus: string;
  degraded: boolean;
  manualReviewRecommended: boolean;
}

export function DecisionCard({
  decision,
  approvedAmount,
  confidenceScore,
  processingStatus,
  degraded,
  manualReviewRecommended,
}: DecisionCardProps) {
  
  const getDecisionConfig = () => {
    switch (decision) {
      case "APPROVED":
        return {
          icon: <CheckCircle2 className="w-10 h-10 text-emerald-500" />,
          bgColor: "bg-emerald-50",
          borderColor: "border-emerald-200",
          textColor: "text-emerald-700",
          title: "Approved",
        };
      case "PARTIAL":
        return {
          icon: <AlertTriangle className="w-10 h-10 text-amber-500" />,
          bgColor: "bg-amber-50",
          borderColor: "border-amber-200",
          textColor: "text-amber-700",
          title: "Partially Approved",
        };
      case "REJECTED":
        return {
          icon: <XCircle className="w-10 h-10 text-rose-500" />,
          bgColor: "bg-rose-50",
          borderColor: "border-rose-200",
          textColor: "text-rose-700",
          title: "Rejected",
        };
      case "MANUAL_REVIEW":
        return {
          icon: <Clock className="w-10 h-10 text-blue-500" />,
          bgColor: "bg-blue-50",
          borderColor: "border-blue-200",
          textColor: "text-blue-700",
          title: "Manual Review Required",
        };
      default:
        if (processingStatus === "BLOCKED_DOCUMENT") {
          return {
            icon: <AlertOctagon className="w-10 h-10 text-slate-500" />,
            bgColor: "bg-slate-50",
            borderColor: "border-slate-200",
            textColor: "text-slate-700",
            title: "Blocked",
          };
        }
        return {
          icon: <Info className="w-10 h-10 text-slate-500" />,
          bgColor: "bg-slate-50",
          borderColor: "border-slate-200",
          textColor: "text-slate-700",
          title: "Unknown",
        };
    }
  };

  const config = getDecisionConfig();
  const formatCurrency = (val?: number) => (val != null ? `₹${val.toFixed(2)}` : "—");
  const formatConfidence = (val?: number) => (val != null ? `${(val * 100).toFixed(0)}%` : "—");

  return (
    <div className={cn("rounded-xl border p-6 flex flex-col gap-6", config.bgColor, config.borderColor)}>
      <div className="flex items-center gap-4 border-b pb-6" style={{ borderColor: 'inherit' }}>
        <div className="bg-white p-3 rounded-xl shadow-sm">
          {config.icon}
        </div>
        <div>
          <h2 className={cn("text-2xl font-bold tracking-tight", config.textColor)}>
            {config.title}
          </h2>
          <p className={cn("text-sm font-medium mt-1 opacity-80", config.textColor)}>
            Status: {processingStatus.replace(/_/g, " ")}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="bg-white/60 p-4 rounded-lg">
          <p className="text-sm font-medium text-slate-500">Approved Amount</p>
          <p className="text-3xl font-bold text-slate-900 mt-1">
            {formatCurrency(approvedAmount)}
          </p>
        </div>
        <div className="bg-white/60 p-4 rounded-lg">
          <p className="text-sm font-medium text-slate-500">System Confidence</p>
          <div className="flex items-baseline gap-2 mt-1">
            <p className="text-3xl font-bold text-slate-900">
              {formatConfidence(confidenceScore)}
            </p>
            {confidenceScore != null && confidenceScore < 0.8 && (
              <span className="text-xs font-semibold text-amber-600 bg-amber-100 px-2 py-0.5 rounded-full">
                Low Confidence
              </span>
            )}
          </div>
        </div>
      </div>

      {(manualReviewRecommended || degraded) && (
        <div className="bg-amber-100 border border-amber-200 p-4 rounded-lg flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
          <div>
            <h4 className="text-sm font-semibold text-amber-900">
              {manualReviewRecommended ? "Manual Review Recommended" : "Degraded Processing"}
            </h4>
            <p className="text-sm text-amber-800 mt-1">
              The system recommends human review due to incomplete processing, component failure, or a triggered policy rule.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
