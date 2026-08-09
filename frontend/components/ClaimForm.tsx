"use client";

import { useState, type FormEvent } from "react";
import { UploadCloud, CheckCircle, AlertCircle, FileText, Trash2 } from "lucide-react";
import { cn } from "../app/utils";
import type { ClaimSubmission, DocumentArtifact } from "../app/types";

type UploadResult = {
  document_id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ClaimFormProps {
  onSubmit: (submission: ClaimSubmission) => Promise<void>;
  isLoading: boolean;
}

export function ClaimForm({ onSubmit, isLoading }: ClaimFormProps) {
  const [form, setForm] = useState({
    memberId: "",
    policyId: "PLUM_GHI_2024",
    category: "CONSULTATION",
    treatmentDate: "",
    claimAmount: "",
    simulateFailure: false,
  });

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [uploadedDocs, setUploadedDocs] = useState<DocumentArtifact[]>([]);

  const handleFieldChange = (field: keyof typeof form, value: string | boolean) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleFileUpload = async () => {
    if (!selectedFile) return;

    setIsUploading(true);
    setUploadError("");

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const response = await fetch(`${apiUrl}/api/documents/upload`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Upload failed");
      }

      setUploadedDocs((prev) => [
        ...prev,
        {
          file_id: data.document_id,
          file_name: data.filename,
          mime_type: data.content_type,
          size_bytes: data.size_bytes,
        },
      ]);
      setSelectedFile(null);
      // Reset input element
      const fileInput = document.getElementById("document-upload") as HTMLInputElement;
      if (fileInput) fileInput.value = "";
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setIsUploading(false);
    }
  };

  const removeDocument = (id: string) => {
    setUploadedDocs((prev) => prev.filter((d) => d.file_id !== id));
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!form.memberId || !form.treatmentDate || !form.claimAmount) {
      alert("Please fill in all required fields.");
      return;
    }
    
    if (uploadedDocs.length === 0) {
      alert("Please upload at least one document.");
      return;
    }

    const submission: ClaimSubmission = {
      member_id: form.memberId,
      policy_id: form.policyId,
      claim_category: form.category,
      treatment_date: form.treatmentDate,
      claimed_amount: parseFloat(form.claimAmount),
      simulate_component_failure: form.simulateFailure,
      documents: uploadedDocs,
    };

    await onSubmit(submission);
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden"
    >
      <div className="bg-slate-50 border-b border-slate-200 px-6 py-4">
        <h2 className="text-lg font-semibold text-slate-800">Submit New Claim</h2>
        <p className="text-sm text-slate-500 mt-1">
          Enter claim details and upload supporting documents.
        </p>
      </div>

      <div className="p-6 space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-700">Member ID *</label>
            <input
              type="text"
              required
              placeholder="e.g. EMP001"
              value={form.memberId}
              onChange={(e) => handleFieldChange("memberId", e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-700">Policy ID</label>
            <input
              type="text"
              value={form.policyId}
              onChange={(e) => handleFieldChange("policyId", e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-700">Category *</label>
            <select
              value={form.category}
              onChange={(e) => handleFieldChange("category", e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
            >
              <option value="CONSULTATION">Consultation</option>
              <option value="DIAGNOSTIC">Diagnostic</option>
              <option value="PHARMACY">Pharmacy</option>
              <option value="DENTAL">Dental</option>
              <option value="VISION">Vision</option>
              <option value="ALTERNATIVE_MEDICINE">Alternative Medicine</option>
            </select>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-700">Treatment Date *</label>
            <input
              type="date"
              required
              value={form.treatmentDate}
              onChange={(e) => handleFieldChange("treatmentDate", e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-700">Claim Amount (₹) *</label>
            <input
              type="number"
              required
              min="0"
              step="0.01"
              placeholder="0.00"
              value={form.claimAmount}
              onChange={(e) => handleFieldChange("claimAmount", e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
            />
          </div>
        </div>

        <div className="pt-4 border-t border-slate-200">
          <label className="flex items-center space-x-3 p-3 rounded-lg border border-amber-200 bg-amber-50 cursor-pointer hover:bg-amber-100 transition-colors">
            <input
              type="checkbox"
              checked={form.simulateFailure}
              onChange={(e) => handleFieldChange("simulateFailure", e.target.checked)}
              className="w-4 h-4 text-amber-600 rounded border-amber-300 focus:ring-amber-500"
            />
            <div className="flex flex-col">
              <span className="text-sm font-medium text-amber-900">Simulate Component Failure (TC011 Demo)</span>
              <span className="text-xs text-amber-700">Intentionally fail the Fraud Analysis stage to demonstrate graceful degradation.</span>
            </div>
          </label>
        </div>

        <div className="pt-4 border-t border-slate-200">
          <h3 className="text-sm font-medium text-slate-700 mb-4">Documents</h3>
          
          <div className="flex items-start gap-4 mb-6">
            <div className="flex-1">
              <input
                id="document-upload"
                type="file"
                accept=".pdf,.png,.jpg,.jpeg,.webp,application/pdf,image/png,image/jpeg,image/webp"
                onChange={(e) => {
                  setSelectedFile(e.target.files?.[0] || null);
                  setUploadError("");
                }}
                className="block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
              />
            </div>
            <button
              type="button"
              onClick={handleFileUpload}
              disabled={!selectedFile || isUploading}
              className={cn(
                "px-4 py-2 rounded-full text-sm font-semibold flex items-center gap-2",
                !selectedFile || isUploading
                  ? "bg-slate-100 text-slate-400 cursor-not-allowed"
                  : "bg-blue-600 text-white hover:bg-blue-700 shadow-sm"
              )}
            >
              <UploadCloud className="w-4 h-4" />
              {isUploading ? "Uploading..." : "Upload"}
            </button>
          </div>

          {uploadError && (
            <div className="flex items-center gap-2 text-sm text-red-600 bg-red-50 p-3 rounded-lg mb-4 border border-red-100">
              <AlertCircle className="w-4 h-4" />
              {uploadError}
            </div>
          )}

          {uploadedDocs.length > 0 && (
            <div className="space-y-2">
              {uploadedDocs.map((doc) => (
                <div key={doc.file_id} className="flex items-center justify-between p-3 bg-slate-50 border border-slate-200 rounded-lg">
                  <div className="flex items-center gap-3">
                    <FileText className="w-5 h-5 text-slate-400" />
                    <div>
                      <p className="text-sm font-medium text-slate-700">{doc.file_name}</p>
                      <p className="text-xs text-slate-500">
                        {doc.mime_type} • {doc.size_bytes ? (doc.size_bytes / 1024).toFixed(1) + " KB" : "Unknown size"}
                      </p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => removeDocument(doc.file_id)}
                    className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-full transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="bg-slate-50 border-t border-slate-200 px-6 py-4 flex justify-end">
        <button
          type="submit"
          disabled={isLoading || uploadedDocs.length === 0}
          className={cn(
            "px-6 py-2.5 rounded-lg text-sm font-semibold flex items-center gap-2 transition-all",
            isLoading || uploadedDocs.length === 0
              ? "bg-slate-200 text-slate-500 cursor-not-allowed"
              : "bg-slate-900 text-white hover:bg-slate-800 shadow-md"
          )}
        >
          {isLoading ? (
            <div className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
          ) : (
            <CheckCircle className="w-4 h-4" />
          )}
          {isLoading ? "Processing Claim..." : "Submit Claim"}
        </button>
      </div>
    </form>
  );
}
