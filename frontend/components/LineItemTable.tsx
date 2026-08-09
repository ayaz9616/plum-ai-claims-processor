import { CheckCircle2, XCircle } from "lucide-react";

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
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden mb-8">
      <div className="px-6 py-4 border-b border-slate-200 bg-slate-50">
        <h3 className="font-semibold text-slate-900">Line Items</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm text-left">
          <thead className="bg-slate-50/50 text-slate-500 font-medium border-b border-slate-200">
            <tr>
              <th className="px-6 py-3">Description</th>
              <th className="px-6 py-3 text-right">Claimed</th>
              <th className="px-6 py-3 text-center">Status</th>
              <th className="px-6 py-3 text-right">Approved</th>
              <th className="px-6 py-3">Reason</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {lineItems.map((item, idx) => (
              <tr key={idx} className="hover:bg-slate-50/50 transition-colors">
                <td className="px-6 py-4 font-medium text-slate-900">{item.description}</td>
                <td className="px-6 py-4 text-right text-slate-600">
                  {item.claimed_amount ? `₹${item.claimed_amount}` : "-"}
                </td>
                <td className="px-6 py-4 text-center">
                  {item.eligible === true ? (
                    <span className="inline-flex items-center gap-1 text-green-700 bg-green-50 px-2 py-1 rounded-md text-xs font-medium">
                      <CheckCircle2 className="w-3.5 h-3.5" /> Eligible
                    </span>
                  ) : item.eligible === false ? (
                    <span className="inline-flex items-center gap-1 text-red-700 bg-red-50 px-2 py-1 rounded-md text-xs font-medium">
                      <XCircle className="w-3.5 h-3.5" /> Ineligible
                    </span>
                  ) : (
                    <span className="text-slate-400">-</span>
                  )}
                </td>
                <td className="px-6 py-4 text-right font-medium text-slate-900">
                  {item.approved_amount ? `₹${item.approved_amount}` : "-"}
                </td>
                <td className="px-6 py-4 text-slate-500">
                  {item.reason || "-"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
