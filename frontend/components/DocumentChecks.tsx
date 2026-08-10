import { useState } from "react";
import { FileCheck, FileWarning, AlertCircle, FileText, Search, XCircle, CheckCircle2 } from "lucide-react";
import { cn } from "../app/utils";
import type { TraceEvent } from "../app/types";
import { Modal } from "./Modal";

interface DocumentChecksProps {
  status: string;
  message: string;
  required: string[];
  provided: string[];
  missing: string[];
  unreadable: string[];
  wrongType: string[];
  extractionTrace?: TraceEvent;
}

export function DocumentChecks({
  status,
  message,
  required,
  provided,
  missing,
  unreadable,
  wrongType,
  extractionTrace,
}: DocumentChecksProps) {
  const isOk = status === "VERIFIED" || status === "OK";
  const [selectedDoc, setSelectedDoc] = useState<any | null>(null);

  const extractions = Array.isArray(extractionTrace?.safe_output) ? extractionTrace.safe_output : [];

  return (
    <div className="space-y-6">
      {!isOk && (
        <div className="bg-danger/5 border border-danger/20 p-4 rounded-xl flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-danger shrink-0 mt-0.5" />
          <div>
            <h3 className="text-sm font-semibold text-danger">Verification Issue</h3>
            <p className="text-sm text-danger/80 mt-1">{message}</p>
          </div>
        </div>
      )}

      <div className="flex gap-4 overflow-x-auto pb-4 snap-x">
        {/* Render provided documents from extraction trace */}
        {extractions.map((doc: any, i: number) => {
          const isUnreadable = unreadable.includes(doc.file_id) || doc.quality === "UNREADABLE";
          const isLow = doc.quality === "LOW";
          
          return (
            <div 
              key={doc.file_id || i}
              onClick={() => setSelectedDoc(doc)}
              className="snap-start shrink-0 w-64 bg-white rounded-2xl border border-plum-900/10 shadow-sm hover:shadow-elevated transition-all cursor-pointer group flex flex-col overflow-hidden"
            >
              <div className="h-32 bg-cream-50 border-b border-plum-900/5 flex items-center justify-center relative overflow-hidden">
                <FileText className="w-12 h-12 text-plum-900/10 group-hover:scale-110 transition-transform" />
                <div className="absolute inset-0 bg-plum-900/0 group-hover:bg-plum-900/5 transition-colors flex items-center justify-center">
                  <div className="opacity-0 group-hover:opacity-100 bg-white shadow-soft rounded-full p-2 text-plum-900 transform translate-y-2 group-hover:translate-y-0 transition-all">
                    <Search size={16} />
                  </div>
                </div>
              </div>
              <div className="p-4 flex-1 flex flex-col justify-between">
                <div>
                  <h4 className="font-medium text-plum-900 text-sm truncate" title={doc.document_type}>
                    {doc.document_type.replace(/_/g, " ")}
                  </h4>
                  <p className="text-xs text-text-secondary mt-1 font-mono truncate" title={doc.file_id}>
                    {doc.file_id}
                  </p>
                </div>
                <div className="mt-4 flex items-center gap-1.5">
                  {isUnreadable ? (
                    <><XCircle className="w-4 h-4 text-danger" /><span className="text-xs font-medium text-danger">Unreadable</span></>
                  ) : isLow ? (
                    <><AlertCircle className="w-4 h-4 text-warning" /><span className="text-xs font-medium text-warning">Low Quality</span></>
                  ) : (
                    <><CheckCircle2 className="w-4 h-4 text-success" /><span className="text-xs font-medium text-success">Good Quality</span></>
                  )}
                </div>
              </div>
            </div>
          );
        })}

        {/* Render missing required documents */}
        {missing.map((req, i) => (
          <div key={`missing-${i}`} className="snap-start shrink-0 w-64 bg-cream-50 rounded-2xl border-2 border-dashed border-danger/30 flex flex-col items-center justify-center p-6 text-center">
            <FileWarning className="w-8 h-8 text-danger/40 mb-3" />
            <h4 className="font-medium text-danger/80 text-sm">{req.replace(/_/g, " ")}</h4>
            <span className="text-xs font-bold uppercase tracking-wider text-danger mt-2 bg-danger/10 px-2 py-0.5 rounded">Missing</span>
          </div>
        ))}
      </div>

      {/* Document Viewer Modal */}
      <Modal isOpen={!!selectedDoc} onClose={() => setSelectedDoc(null)}>
        {selectedDoc && (
          <div className="flex flex-col md:flex-row h-full min-h-[60vh] max-h-[85vh]">
            <div className="md:w-1/2 bg-cream-100 flex items-center justify-center p-8 border-r border-plum-900/10 min-h-[300px]">
              <div className="text-center">
                <FileText className="w-24 h-24 text-plum-900/20 mx-auto mb-4" />
                <p className="text-text-secondary text-sm">Document viewer placeholder.</p>
                <p className="text-text-secondary text-xs mt-1">In production, this would render the PDF/Image.</p>
                <div className="mt-4 bg-white px-4 py-2 rounded-lg text-sm font-mono text-plum-900 shadow-sm border border-plum-900/10">
                  {selectedDoc.file_id}
                </div>
              </div>
            </div>
            <div className="md:w-1/2 bg-white flex flex-col max-h-[85vh]">
              <div className="p-6 border-b border-plum-900/5 bg-cream-50 shrink-0">
                <h3 className="font-serif text-2xl text-plum-900">{selectedDoc.document_type.replace(/_/g, " ")}</h3>
                <div className="flex items-center gap-2 mt-2">
                  <span className="text-xs font-medium text-text-secondary uppercase tracking-wider">Quality:</span>
                  <span className={cn("text-xs font-bold uppercase tracking-wider px-2 py-0.5 rounded", selectedDoc.quality === "UNREADABLE" ? "bg-danger/10 text-danger" : selectedDoc.quality === "LOW" ? "bg-warning/10 text-warning" : "bg-success/10 text-success")}>
                    {selectedDoc.quality}
                  </span>
                </div>
              </div>
              <div className="p-6 overflow-y-auto flex-1">
                <h4 className="text-[11px] font-bold tracking-widest text-plum-900/40 uppercase mb-4">Extracted Data</h4>
                <div className="space-y-4">
                  {Object.entries(selectedDoc.extracted || {}).map(([key, value]) => {
                    if (key === "line_items") return null;
                    return (
                      <div key={key}>
                        <p className="text-xs text-text-secondary uppercase tracking-wider mb-1">{key.replace(/_/g, " ")}</p>
                        <p className="text-sm font-medium text-plum-900">{value !== null && value !== "" ? String(value) : <span className="text-plum-900/30 italic">Not found</span>}</p>
                      </div>
                    );
                  })}
                  {selectedDoc.extracted?.line_items && selectedDoc.extracted.line_items.length > 0 && (
                    <div className="mt-6 pt-6 border-t border-plum-900/10">
                      <p className="text-xs text-text-secondary uppercase tracking-wider mb-3">Line Items</p>
                      <div className="space-y-2">
                        {selectedDoc.extracted.line_items.map((item: any, i: number) => (
                          <div key={i} className="flex justify-between items-center text-sm bg-cream-50 p-2 rounded">
                            <span className="text-plum-900 truncate pr-4">{item.description}</span>
                            <span className="font-medium text-plum-900 shrink-0">₹{item.amount}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
