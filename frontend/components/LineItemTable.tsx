import { CheckCircle2, XCircle } from "lucide-react";
import { formatCurrency } from "../app/utils";
import { cn } from "../app/utils";

export type LineItem = {
  description: string;
  claimed_amount?: number | string;
  eligible?: boolean;
  approved_amount?: number | string;
  reason?: string;
};

export function LineItemTable({
  lineItems,
}: {
  lineItems: LineItem[];
}) {
  if (!lineItems || lineItems.length === 0) return null;

  return (
    <div>
      <h3 className="text-[11px] font-bold tracking-widest text-plum-900/40 uppercase mb-4">Line Items</h3>
      <div className="space-y-3">
        {lineItems.map((item, idx) => (
          <div key={idx} className={cn(
            "flex items-center justify-between gap-4 p-4 rounded-xl border transition-colors",
            item.eligible === false ? "bg-danger/5 border-danger/10" : "bg-cream-50 border-plum-900/5 hover:bg-cream-100"
          )}>
            <div className="flex items-center gap-3 min-w-0 flex-1">
              {item.eligible === true ? (
                <CheckCircle2 className="w-5 h-5 text-success shrink-0" />
              ) : item.eligible === false ? (
                <XCircle className="w-5 h-5 text-danger shrink-0" />
              ) : null}
              <div className="min-w-0">
                <p className="text-sm font-medium text-plum-900 truncate">{item.description}</p>
                {item.reason && <p className="text-xs text-text-secondary mt-0.5">{item.reason}</p>}
              </div>
            </div>
            <div className="text-right shrink-0">
              {item.eligible === false && item.claimed_amount != null ? (
                <p className="text-sm font-medium text-danger">{formatCurrency(item.claimed_amount)}</p>
              ) : item.approved_amount != null ? (
                <p className="text-sm font-medium text-plum-900">{formatCurrency(item.approved_amount)}</p>
              ) : item.claimed_amount != null ? (
                <p className="text-sm font-medium text-plum-900">{formatCurrency(item.claimed_amount)}</p>
              ) : null}
              {item.eligible === false && (
                <p className="text-xs text-danger mt-0.5">Excluded</p>
              )}
              {item.eligible === true && item.claimed_amount != null && item.approved_amount !== item.claimed_amount && (
                <p className="text-xs text-text-secondary">{formatCurrency(item.claimed_amount)} claimed</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

