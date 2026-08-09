import { CheckCircle, Circle, AlertCircle } from "lucide-react";
import { cn } from "../app/utils";

const STAGES = [
  "Upload",
  "Document Verification",
  "Policy Evaluation",
  "Financial Calculation",
  "Fraud Analysis",
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
    <div className="flex flex-col sm:flex-row items-center justify-between w-full max-w-4xl mx-auto py-8">
      {STAGES.map((stage, i) => {
        const isCompleted = i < currentStageIndex;
        const isCurrent = i === currentStageIndex;
        const isFailed = isCurrent && isError;
        const isPending = i > currentStageIndex;

        return (
          <div key={stage} className="flex flex-col items-center flex-1 relative group">
            {/* Connecting line */}
            {i !== STAGES.length - 1 && (
              <div
                className={cn(
                  "hidden sm:block absolute top-4 left-[50%] right-[-50%] h-0.5",
                  isCompleted ? "bg-blue-600" : "bg-slate-200"
                )}
              />
            )}
            
            <div
              className={cn(
                "relative z-10 flex items-center justify-center w-8 h-8 rounded-full border-2 bg-white",
                isCompleted && "border-blue-600 text-blue-600",
                isCurrent && !isFailed && "border-blue-600 bg-blue-50 text-blue-600",
                isFailed && "border-red-500 bg-red-50 text-red-500",
                isPending && "border-slate-300 text-slate-300"
              )}
            >
              {isCompleted ? (
                <CheckCircle className="w-5 h-5" />
              ) : isFailed ? (
                <AlertCircle className="w-5 h-5" />
              ) : isCurrent ? (
                <div className="w-2.5 h-2.5 rounded-full bg-blue-600 animate-pulse" />
              ) : (
                <Circle className="w-5 h-5" />
              )}
            </div>
            
            <p
              className={cn(
                "mt-3 text-xs font-medium text-center",
                isCompleted || isCurrent ? "text-slate-900" : "text-slate-400",
                isFailed && "text-red-600"
              )}
            >
              {stage}
            </p>
          </div>
        );
      })}
    </div>
  );
}
