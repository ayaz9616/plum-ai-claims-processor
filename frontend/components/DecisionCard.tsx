import { CheckCircle2, XCircle, Clock, AlertTriangle, AlertOctagon, Info, ArrowRight } from "lucide-react";
import { cn, formatCurrency, formatPercentage } from "../app/utils";
import type { TraceEvent } from "../app/types";

interface DecisionCardProps {
  decision?: string;
  approvedAmount?: number;
  reimbursableAmount?: number;
  confidenceScore?: number;
  processingStatus: string;
  degraded: boolean;
  manualReviewRecommended: boolean;
  decisionSummary?: string;
  trace?: TraceEvent[];
}

export function DecisionCard({
  decision,
  approvedAmount,
  reimbursableAmount,
  confidenceScore,
  processingStatus,
  degraded,
  manualReviewRecommended,
  decisionSummary,
}: DecisionCardProps) {
  
  const getDecisionConfig = () => {
    switch (decision) {
      case "APPROVED":
        return {
          icon: <CheckCircle2 className="w-12 h-12 text-success" />,
          bgColor: "bg-plum-900",
          textColor: "text-cream-50",
          secondaryTextColor: "text-cream-100/80",
          badgeBg: "bg-success/20",
          badgeText: "text-success",
          title: "Approved",
          accentColor: "text-coral-500",
        };
      case "PARTIAL":
        return {
          icon: <AlertTriangle className="w-12 h-12 text-warning" />,
          bgColor: "bg-plum-900",
          textColor: "text-cream-50",
          secondaryTextColor: "text-cream-100/80",
          badgeBg: "bg-warning/20",
          badgeText: "text-warning",
          title: "Partially Approved",
          accentColor: "text-coral-400",
        };
      case "REJECTED":
        return {
          icon: <XCircle className="w-12 h-12 text-danger" />,
          bgColor: "bg-danger",
          textColor: "text-white",
          secondaryTextColor: "text-white/80",
          badgeBg: "bg-white/20",
          badgeText: "text-white",
          title: "Rejected",
          accentColor: "text-plum-900",
        };
      case "MANUAL_REVIEW":
        return {
          icon: <Clock className="w-12 h-12 text-warning" />,
          bgColor: "bg-[#FFF4E6]", // Custom amber tint
          textColor: "text-plum-900",
          secondaryTextColor: "text-plum-900/70",
          badgeBg: "bg-warning/20",
          badgeText: "text-warning",
          title: "Manual Review Required",
          accentColor: "text-coral-500",
        };
      case "BLOCKED":
        return { 
          icon: <AlertOctagon className="w-12 h-12 text-plum-900" />, 
          bgColor: "bg-cream-100", 
          textColor: "text-plum-900", 
          secondaryTextColor: "text-plum-900/70",
          badgeBg: "bg-plum-900/10",
          badgeText: "text-plum-900",
          title: "Blocked",
          accentColor: "text-plum-900"
        };
      default:
        if (processingStatus.startsWith("BLOCKED")) {
          return {
            icon: <AlertOctagon className="w-12 h-12 text-plum-900" />,
            bgColor: "bg-cream-100",
            textColor: "text-plum-900",
            secondaryTextColor: "text-plum-900/70",
            badgeBg: "bg-plum-900/10",
            badgeText: "text-plum-900",
            title: "Blocked",
            accentColor: "text-plum-900"
          };
        }
        return {
          icon: <Info className="w-12 h-12 text-plum-900" />,
          bgColor: "bg-cream-100",
          textColor: "text-plum-900",
          secondaryTextColor: "text-plum-900/70",
          badgeBg: "bg-plum-900/10",
          badgeText: "text-plum-900",
          title: "Unknown",
          accentColor: "text-plum-900"
        };
    }
  };

  const config = getDecisionConfig();
  const isManualReview = decision === "MANUAL_REVIEW";
  const showPayment = isManualReview || decision === "APPROVED" || decision === "PARTIAL" || decision === "REJECTED" || (decision === "BLOCKED" && reimbursableAmount != null);
  const paymentAmount = isManualReview ? reimbursableAmount : approvedAmount;

  return (
    <div className={cn("rounded-3xl p-8 md:p-12 shadow-elevated relative overflow-hidden transition-colors duration-500", config.bgColor, config.textColor)}>
      
      {/* Background decoration */}
      <div className="absolute -top-24 -right-24 w-64 h-64 bg-white/5 rounded-full blur-3xl" aria-hidden="true" />
      <div className="absolute -bottom-24 -left-24 w-64 h-64 bg-black/5 rounded-full blur-3xl" aria-hidden="true" />

      <div className="relative z-10 flex flex-col gap-8 md:gap-12">
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-6">
          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-3">
              {config.icon}
              <div className={cn("px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider", config.badgeBg, config.badgeText)}>
                {processingStatus.replace(/_/g, " ")}
              </div>
            </div>
            
            <h2 className="text-5xl md:text-6xl font-serif leading-tight">
              {showPayment && paymentAmount != null && decision !== "REJECTED" && decision !== "BLOCKED" ? (
                <>
                  {formatCurrency(paymentAmount)} <br className="hidden md:block" />
                  <span className={cn("text-3xl md:text-4xl", config.secondaryTextColor)}>
                    {isManualReview ? "Estimated" : "Approved"}
                  </span>
                </>
              ) : (
                config.title
              )}
            </h2>
          </div>

          <div className="flex flex-col gap-4 shrink-0">
            <div className="bg-black/5 backdrop-blur-md rounded-2xl p-6 border border-white/10 min-w-[200px]">
              <p className={cn("text-sm font-medium mb-1 uppercase tracking-widest", config.secondaryTextColor)}>Confidence</p>
              <div className="flex items-baseline gap-2">
                <p className="text-4xl font-serif">
                  {formatPercentage(confidenceScore)}
                </p>
              </div>
              {confidenceScore != null && confidenceScore < 0.8 && (
                <p className="text-xs font-medium mt-2 text-warning flex items-center gap-1">
                  <AlertTriangle size={12} /> Low Confidence
                </p>
              )}
            </div>
          </div>
        </div>

        {decisionSummary && (
          <div className="pt-8 border-t border-white/10 flex flex-col md:flex-row gap-6 items-start md:items-center justify-between">
            <div className="flex-1 max-w-3xl">
              <p className={cn("text-sm font-bold uppercase tracking-widest mb-2", config.secondaryTextColor)}>Why this decision?</p>
              <p className="text-lg md:text-xl font-medium leading-relaxed font-serif">
                {decisionSummary}
              </p>
            </div>
          </div>
        )}

        {(manualReviewRecommended || degraded) && (
          <div className="bg-warning/20 border border-warning/30 p-4 rounded-xl flex items-start gap-3 backdrop-blur-md">
            <AlertTriangle className="w-5 h-5 text-warning shrink-0 mt-0.5" />
            <div>
              <h4 className="text-sm font-bold text-warning uppercase tracking-wider">
                {manualReviewRecommended ? "Manual Review Recommended" : "Degraded Processing"}
              </h4>
              <p className={cn("text-sm mt-1", config.secondaryTextColor)}>
                The system recommends human review due to incomplete processing, component failure, or a triggered policy rule.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
