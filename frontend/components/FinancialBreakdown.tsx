import { ArrowDown, Minus } from "lucide-react";
import { cn, formatCurrency } from "../app/utils";
import type { TraceEvent } from "../app/types";

interface FinancialBreakdownProps {
  claimed: string | number;
  networkApplied: boolean;
  networkDiscount: string | number;
  copay: string | number;
  approved: string | number;
  excluded?: string | number;
  copayPercent?: string | number;
  estimated?: boolean;
  isDental?: boolean;
  financeTrace?: TraceEvent;
}

export function FinancialBreakdown({
  claimed,
  networkApplied,
  networkDiscount,
  copay,
  approved,
  excluded = 0,
  copayPercent,
  estimated = false,
  isDental = false,
  financeTrace,
}: FinancialBreakdownProps) {
  const claimedAmount = Number(claimed);
  const approvedAmount = Number(approved);
  const excludedAmount = Number(excluded);

  return (
    <div className="bg-white rounded-2xl shadow-soft border border-plum-900/5 p-6 md:p-8 flex flex-col">
      <h3 className="text-[11px] font-bold tracking-widest text-plum-900/40 uppercase mb-6">Waterfall</h3>

      <div className="flex items-center justify-between py-4">
        <span className="text-sm text-text-secondary">Claimed</span>
        <span className="text-2xl font-serif text-plum-900">{formatCurrency(claimedAmount)}</span>
      </div>

      {isDental && excludedAmount > 0 && (
        <>
          <div className="flex justify-center py-1">
            <ArrowDown size={16} className="text-plum-900/20" />
          </div>
          <div className="flex items-center justify-between py-3 px-4 bg-danger/5 rounded-xl border border-danger/10">
            <div className="flex items-center gap-2">
              <Minus size={14} className="text-danger" />
              <span className="text-sm text-danger font-medium">Excluded</span>
            </div>
            <span className="text-lg font-medium text-danger">-{formatCurrency(excludedAmount)}</span>
          </div>
        </>
      )}

      {networkApplied && Number(networkDiscount) > 0 && (
        <>
          <div className="flex justify-center py-1">
            <ArrowDown size={16} className="text-plum-900/20" />
          </div>
          <div className="flex items-center justify-between py-3 px-4 bg-success/5 rounded-xl border border-success/10">
            <div className="flex items-center gap-2">
              <Minus size={14} className="text-success" />
              <span className="text-sm text-success font-medium">Network Discount</span>
            </div>
            <span className="text-lg font-medium text-success">-{formatCurrency(Number(networkDiscount))}</span>
          </div>
        </>
      )}

      {Number(copay) > 0 && (
        <>
          <div className="flex justify-center py-1">
            <ArrowDown size={16} className="text-plum-900/20" />
          </div>
          <div className="flex items-center justify-between py-3 px-4 bg-warning/5 rounded-xl border border-warning/10">
            <div className="flex items-center gap-2">
              <Minus size={14} className="text-warning" />
              <span className="text-sm text-warning font-medium">
                Co-pay {copayPercent != null ? `(${copayPercent}%)` : ""}
              </span>
            </div>
            <span className="text-lg font-medium text-warning">-{formatCurrency(Number(copay))}</span>
          </div>
        </>
      )}

      <div className="flex justify-center py-1">
        <ArrowDown size={16} className="text-plum-900/20" />
      </div>
      <div className="flex items-center justify-between py-4 px-5 bg-plum-900 rounded-2xl mt-1">
        <span className="text-sm font-medium text-cream-100/80">
          {estimated ? "Estimated" : "Approved"}
        </span>
        <span className="text-3xl font-serif text-cream-50">{formatCurrency(approvedAmount)}</span>
      </div>

      {estimated && (
        <p className="text-xs text-text-secondary mt-3 text-center">Estimated — pending manual verification</p>
      )}
    </div>
  );
}
