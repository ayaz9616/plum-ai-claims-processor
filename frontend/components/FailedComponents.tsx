import { AlertTriangle } from "lucide-react";

export function FailedComponents({
  failures,
}: {
  failures: Array<{ component?: string; severity?: string; reason?: string }>;
}) {
  if (!failures || failures.length === 0) return null;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-orange-200 overflow-hidden mb-8">
      <div className="bg-orange-50 px-6 py-4 border-b border-orange-200 flex items-center gap-2">
        <AlertTriangle className="w-5 h-5 text-orange-600" />
        <h3 className="font-semibold text-orange-900">Failed Components</h3>
      </div>
      <div className="p-6">
        <div className="space-y-4">
          {failures.map((failure, idx) => (
            <div key={idx} className="flex flex-col sm:flex-row sm:items-start gap-4 p-4 rounded-lg bg-orange-50/50 border border-orange-100">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-medium text-orange-900">{failure.component || "Unknown Component"}</span>
                  <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-orange-200 text-orange-800">
                    {failure.severity || "UNKNOWN_SEVERITY"}
                  </span>
                </div>
                <p className="text-sm text-orange-800">{failure.reason || "No reason provided."}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
