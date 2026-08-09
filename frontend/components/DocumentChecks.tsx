import { FileCheck, FileWarning, AlertCircle } from "lucide-react";
import { cn } from "../app/utils";

interface DocumentChecksProps {
  status: string;
  message: string;
  required: string[];
  provided: string[];
  missing: string[];
  unreadable: string[];
  wrongType: string[];
}

export function DocumentChecks({
  status,
  message,
  required,
  provided,
  missing,
  unreadable,
  wrongType,
}: DocumentChecksProps) {
  const isOk = status === "VERIFIED" || status === "OK";

  return (
    <div className="rounded-xl border border-slate-200 bg-white overflow-hidden shadow-sm">
      <div className={cn("px-6 py-4 border-b flex items-center gap-3", isOk ? "bg-slate-50" : "bg-red-50")}>
        {isOk ? <FileCheck className="w-5 h-5 text-emerald-600" /> : <FileWarning className="w-5 h-5 text-red-600" />}
        <div>
          <h3 className="text-lg font-semibold text-slate-800">Document Verification</h3>
          <p className="text-sm text-slate-500">{message}</p>
        </div>
      </div>
      
      <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <h4 className="text-sm font-medium text-slate-700 mb-3 border-b pb-2">Requirements</h4>
          <div className="space-y-2">
            <p className="text-sm"><span className="text-slate-500">Required:</span> {required.length > 0 ? required.join(", ") : "None"}</p>
            <p className="text-sm"><span className="text-slate-500">Provided:</span> {provided.length > 0 ? provided.join(", ") : "None"}</p>
          </div>
        </div>
        
        {(missing.length > 0 || unreadable.length > 0 || wrongType.length > 0) && (
          <div>
            <h4 className="text-sm font-medium text-red-700 mb-3 border-b border-red-100 pb-2">Issues Found</h4>
            <ul className="space-y-2">
              {missing.map((m) => (
                <li key={m} className="text-sm text-red-600 flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                  Missing required document: {m}
                </li>
              ))}
              {unreadable.map((u) => (
                <li key={u} className="text-sm text-red-600 flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                  Unreadable document: {u}
                </li>
              ))}
              {wrongType.map((w) => (
                <li key={w} className="text-sm text-red-600 flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                  Unexpected type: {w}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
