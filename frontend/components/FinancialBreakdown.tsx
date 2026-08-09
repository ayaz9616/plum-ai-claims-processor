import { Calculator, ArrowRight } from "lucide-react";
import { cn } from "../app/utils";

interface FinancialBreakdownProps {
  claimed: string | number;
  networkApplied: boolean;
  networkDiscount: string | number;
  copay: string | number;
  approved: string | number;
}

export function FinancialBreakdown({
  claimed,
  networkApplied,
  networkDiscount,
  copay,
  approved,
}: FinancialBreakdownProps) {
  
  const steps = [
    { label: "Claimed Amount", value: claimed, highlight: false },
    ...(networkApplied
      ? [{ label: "Network Discount", value: `-${networkDiscount}`, highlight: true, note: "20% in-network" }]
      : []),
    ...(Number(copay) > 0
      ? [{ label: "Co-pay", value: `-${copay}`, highlight: true, note: "10% co-pay" }]
      : []),
    { label: "Final Approved", value: approved, highlight: true, isFinal: true },
  ];

  return (
    <div className="rounded-xl border border-slate-200 bg-white overflow-hidden shadow-sm">
      <div className="px-6 py-4 border-b bg-slate-50 flex items-center gap-3">
        <Calculator className="w-5 h-5 text-slate-600" />
        <div>
          <h3 className="text-lg font-semibold text-slate-800">Financial Breakdown</h3>
          <p className="text-sm text-slate-500">Deterministic calculation sequence</p>
        </div>
      </div>

      <div className="p-6">
        <div className="flex flex-col gap-4">
          {steps.map((step, index) => (
            <div key={step.label} className="flex items-center gap-4">
              <div className={cn(
                "flex-1 p-4 rounded-lg flex items-center justify-between border",
                step.isFinal ? "bg-emerald-50 border-emerald-200" : "bg-slate-50 border-slate-200"
              )}>
                <div>
                  <p className={cn("text-sm font-medium", step.isFinal ? "text-emerald-900" : "text-slate-700")}>
                    {step.label}
                  </p>
                  {step.note && <p className="text-xs text-slate-500 mt-1">{step.note}</p>}
                </div>
                <p className={cn(
                  "text-lg font-bold tracking-tight",
                  step.isFinal ? "text-emerald-700" : "text-slate-900",
                  step.value.toString().startsWith('-') && "text-rose-600"
                )}>
                  {step.value.toString().startsWith('-') ? '' : '₹'}{step.value.toString().startsWith('-') ? `-₹${step.value.toString().slice(1)}` : step.value}
                </p>
              </div>
              
              {index < steps.length - 1 && (
                <div className="text-slate-300">
                  <ArrowRight className="w-6 h-6" />
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
