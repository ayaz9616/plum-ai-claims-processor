import { CheckCircle2, Circle, AlertTriangle, XCircle, ArrowRight } from "lucide-react";
import { cn } from "../app/utils";

const STAGES = [
  "Claim Received",
  "Documents",
  "Verification",
  "Policy",
  "Calculation",
  "Fraud",
  "Decision",
];

export function ProcessingPipeline({
  currentStageIndex,
  isError,
}: {
  currentStageIndex: number;
  isError: boolean;
}) {
  return (
    <div className="w-full flex items-center gap-1 sm:gap-2 md:gap-4 overflow-x-auto pb-2 scrollbar-hide text-sm">
      {STAGES.map((stage, i) => {
        const isCompleted = i < currentStageIndex;
        const isCurrent = i === currentStageIndex;
        const isFailed = isCurrent && isError;
        const isPending = i > currentStageIndex;

        return (
          <div key={stage} className="flex items-center whitespace-nowrap shrink-0 group cursor-pointer transition-opacity hover:opacity-80">
            <div
              className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 rounded-full border transition-colors",
                isCompleted && "bg-success/10 border-success/20 text-success",
                isCurrent && !isFailed && "bg-info/10 border-info/20 text-info",
                isFailed && "bg-danger/10 border-danger/20 text-danger",
                isPending && "bg-cream-100/50 border-plum-900/10 text-text-secondary"
              )}
            >
              {isCompleted ? (
                <CheckCircle2 className="w-4 h-4" />
              ) : isFailed ? (
                <XCircle className="w-4 h-4" />
              ) : isCurrent ? (
                <div className="w-4 h-4 flex items-center justify-center">
                  <div className="w-2 h-2 rounded-full bg-info animate-pulse" />
                </div>
              ) : (
                <Circle className="w-4 h-4 opacity-50" />
              )}
              <span className={cn("font-medium", (isCompleted || isCurrent || isFailed) ? "" : "opacity-80")}>
                {stage}
              </span>
            </div>
            
            {i !== STAGES.length - 1 && (
              <ArrowRight className={cn(
                "w-4 h-4 ml-1 sm:ml-2 md:ml-4",
                isCompleted ? "text-success/50" : "text-plum-900/20"
              )} />
            )}
          </div>
        );
      })}
    </div>
  );
}
