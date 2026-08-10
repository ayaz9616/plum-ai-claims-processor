"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { CheckCircle, FileText, Trash2, UploadCloud, File, AlertCircle } from "lucide-react";
import { cn, formatCurrency } from "../app/utils";
import type { ClaimSubmission, DocumentArtifact } from "../app/types";

const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const MAX_FILE_SIZE = 10 * 1024 * 1024;
const ACCEPTED_TYPES = new Set(["application/pdf", "image/png", "image/jpeg", "image/webp"]);

type Member = { member_id: string; name: string; relationship?: string };
type FileStatus = "pending" | "uploading" | "uploaded" | "failed";
type SelectedFile = { file: File; key: string; status: FileStatus; error?: string; document?: DocumentArtifact };

interface ClaimFormProps { onSubmit: (submission: ClaimSubmission) => Promise<void>; isLoading: boolean; }

function fileKey(file: File) { return `${file.name}:${file.size}:${file.lastModified}`; }
function fileSize(bytes: number) { return bytes >= 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`; }
function fileType(file: File) { return file.type === "application/pdf" ? "PDF" : "Image"; }

export function ClaimForm({ onSubmit, isLoading }: ClaimFormProps) {
  const [form, setForm] = useState({ memberId: "", policyId: "", category: "CONSULTATION", treatmentDate: "", claimAmount: "", simulateFailure: false });
  const [members, setMembers] = useState<Member[]>([]);
  const [files, setFiles] = useState<SelectedFile[]>([]);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isUploading, setIsUploading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetch(`${apiUrl}/api/members`).then(response => response.ok ? response.json() : null).then(data => {
      if (data?.members) { setMembers(data.members); setForm(current => ({ ...current, policyId: data.policy_id || "" })); }
      else setErrors(current => ({ ...current, memberId: "Employee roster is unavailable. Please try again." }));
    }).catch(() => setErrors(current => ({ ...current, memberId: "Employee roster is unavailable. Please try again." })));
  }, []);

  const setField = (field: keyof typeof form, value: string | boolean) => {
    setForm(current => ({ ...current, [field]: value }));
    setErrors(current => { const next = { ...current }; delete next[field]; return next; });
  };

  const addFiles = (incoming: File[]) => {
    const next: SelectedFile[] = [];
    const invalid: string[] = [];
    const existing = new Set(files.map(item => item.key));
    for (const file of incoming) {
      if (!ACCEPTED_TYPES.has(file.type)) { invalid.push("Unsupported file type. Please upload PNG, JPG, JPEG, PDF, or WEBP."); continue; }
      if (file.size > MAX_FILE_SIZE) { invalid.push(`${file.name} is too large. Maximum allowed size is 10 MB.`); continue; }
      const key = fileKey(file);
      if (existing.has(key)) { invalid.push(`${file.name} is already selected.`); continue; }
      existing.add(key); next.push({ file, key, status: "pending" });
    }
    if (next.length) setFiles(current => [...current, ...next]);
    setErrors(current => ({ ...current, ...(invalid.length ? { documents: invalid.join(" ") } : { documents: "" }) }));
    if (inputRef.current) inputRef.current.value = "";
  };

  const removeFile = (key: string) => setFiles(current => current.filter(item => item.key !== key));

  const validate = () => {
    const next: Record<string, string> = {};
    if (!form.memberId) next.memberId = "Please select an employee.";
    if (!form.policyId) next.policyId = "No policy is available for this employee.";
    if (!form.category) next.category = "Please select a claim category.";
    if (!form.treatmentDate) next.treatmentDate = "Please select a treatment date.";
    if (!form.claimAmount || !Number.isFinite(Number(form.claimAmount)) || Number(form.claimAmount) <= 0) next.claimAmount = "Claim amount must be greater than ₹0.00.";
    if (!files.length) next.documents = "Please upload at least one supporting document.";
    if (files.some(item => item.status === "failed")) next.documents = "Remove or replace files that failed to upload.";
    setErrors(next); return Object.keys(next).length === 0;
  };

  const uploadPendingFiles = async () => {
    const pending = files.filter(item => item.status === "pending");
    if (!pending.length) return files.flatMap(item => item.document ? [item.document] : []);
    setIsUploading(true);
    const uploaded: DocumentArtifact[] = [];
    for (const item of pending) {
      setFiles(current => current.map(file => file.key === item.key ? { ...file, status: "uploading", error: undefined } : file));
      try {
        const body = new FormData(); body.append("file", item.file);
        const response = await fetch(`${apiUrl}/api/documents/upload`, { method: "POST", body });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "Upload failed. Please try again.");
        const document = { file_id: data.document_id, file_name: data.filename, mime_type: data.content_type, size_bytes: data.size_bytes };
        uploaded.push(document);
        setFiles(current => current.map(file => file.key === item.key ? { ...file, status: "uploaded", document } : file));
      } catch (error) {
        const message = error instanceof Error ? error.message : "Upload failed. Please try again.";
        setFiles(current => current.map(file => file.key === item.key ? { ...file, status: "failed", error: message } : file));
        setIsUploading(false); return null;
      }
    }
    setIsUploading(false);
    return uploaded;
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!validate()) return;
    const existing = files.flatMap(item => item.document ? [item.document] : []);
    const newlyUploaded = await uploadPendingFiles();
    if (newlyUploaded === null) return;
    const documents = [...existing, ...newlyUploaded.filter(document => !existing.some(current => current.file_id === document.file_id))];
    if (!documents.length) return;
    await onSubmit({ member_id: form.memberId, policy_id: form.policyId, claim_category: form.category, treatment_date: form.treatmentDate, claimed_amount: Number(form.claimAmount), simulate_component_failure: form.simulateFailure, documents });
  };

  // Drag and drop handlers
  const onDragOver = (e: React.DragEvent) => { e.preventDefault(); setIsDragging(true); };
  const onDragLeave = (e: React.DragEvent) => { e.preventDefault(); setIsDragging(false); };
  const onDrop = (e: React.DragEvent) => { e.preventDefault(); setIsDragging(false); if (e.dataTransfer.files && e.dataTransfer.files.length > 0) { addFiles(Array.from(e.dataTransfer.files)); } };

  return (
    <div className="bg-white rounded-[24px] shadow-elevated overflow-hidden border border-plum-900/5">
      {/* Deep Plum Header / Hero for form */}
      <div className="bg-plum-900 text-cream-50 p-8 md:p-12 relative overflow-hidden bg-plum-gradient">
        <div className="relative z-10">
          <h1 className="font-serif text-3xl md:text-4xl text-cream-50 mb-3">Submit a claim</h1>
          <p className="text-cream-100/80 font-sans text-lg">Let's get the details right.</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="p-8 md:p-12 space-y-12">
        {/* Step 01: Claim Details */}
        <section className="flex flex-col md:flex-row gap-8">
          <div className="w-full md:w-32 shrink-0">
            <div className="text-3xl font-serif text-plum-900/20">01</div>
            <div className="text-sm font-medium text-plum-900 mt-1">Claim details</div>
          </div>
          
          <div className="flex-1 grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-2">
              <label htmlFor="employee" className="text-sm font-medium text-text-primary">Patient *</label>
              <select id="employee" required value={form.memberId} onChange={event => setField("memberId", event.target.value)} className="w-full rounded-xl border border-plum-900/10 bg-cream-50 px-4 py-3 text-sm focus:border-plum-900 focus:outline-none focus:ring-2 focus:ring-plum-900/10 transition-shadow">
                <option value="">Select patient</option>
                {members.map(member => <option key={member.member_id} value={member.member_id}>{member.member_id} — {member.name}</option>)}
              </select>
              {errors.memberId && <p className="text-xs text-danger">{errors.memberId}</p>}
            </div>

            <div className="space-y-2">
              <label htmlFor="policy" className="text-sm font-medium text-text-primary">Policy</label>
              <input id="policy" readOnly value={form.policyId || "Loading policy…"} className="w-full rounded-xl border border-plum-900/5 bg-cream-100/50 px-4 py-3 text-sm text-text-secondary cursor-not-allowed" />
            </div>

            <div className="space-y-2">
              <label htmlFor="category" className="text-sm font-medium text-text-primary">Claim Type *</label>
              <select id="category" value={form.category} onChange={event => setField("category", event.target.value)} className="w-full rounded-xl border border-plum-900/10 bg-cream-50 px-4 py-3 text-sm focus:border-plum-900 focus:outline-none focus:ring-2 focus:ring-plum-900/10 transition-shadow">
                <option value="CONSULTATION">Consultation</option>
                <option value="DIAGNOSTIC">Diagnostic</option>
                <option value="PHARMACY">Pharmacy</option>
                <option value="DENTAL">Dental</option>
                <option value="VISION">Vision</option>
                <option value="ALTERNATIVE_MEDICINE">Alternative Medicine</option>
              </select>
            </div>

            <div className="space-y-2">
              <label htmlFor="treatment-date" className="text-sm font-medium text-text-primary">Treatment Date *</label>
              <input id="treatment-date" type="date" required value={form.treatmentDate} onChange={event => setField("treatmentDate", event.target.value)} className="w-full rounded-xl border border-plum-900/10 bg-cream-50 px-4 py-3 text-sm focus:border-plum-900 focus:outline-none focus:ring-2 focus:ring-plum-900/10 transition-shadow" />
              {errors.treatmentDate && <p className="text-xs text-danger">{errors.treatmentDate}</p>}
            </div>

            <div className="space-y-2 md:col-span-2">
              <label htmlFor="claim-amount" className="text-sm font-medium text-text-primary">Claimed Amount *</label>
              <div className="relative">
                <span className="absolute left-4 top-1/2 -translate-y-1/2 text-text-secondary font-medium">₹</span>
                <input id="claim-amount" type="text" inputMode="decimal" placeholder="0.00" value={form.claimAmount} onChange={event => { const raw = event.target.value.replace(/,/g, "").replace(/[^0-9.]/g, ""); if ((raw.match(/\./g) || []).length <= 1) setField("claimAmount", raw); }} onBlur={() => form.claimAmount && Number.isFinite(Number(form.claimAmount)) && setField("claimAmount", Number(form.claimAmount).toFixed(2))} className="w-full rounded-xl border border-plum-900/10 bg-cream-50 pl-8 pr-4 py-3 text-sm focus:border-plum-900 focus:outline-none focus:ring-2 focus:ring-plum-900/10 transition-shadow" />
              </div>
              {form.claimAmount && Number.isFinite(Number(form.claimAmount)) && <p className="text-xs text-text-secondary">Display: {formatCurrency(Number(form.claimAmount))}</p>}
              {errors.claimAmount && <p className="text-xs text-danger">{errors.claimAmount}</p>}
            </div>
          </div>
        </section>

        <hr className="border-plum-900/5" />

        {/* Step 02: Documents */}
        <section className="flex flex-col md:flex-row gap-8">
          <div className="w-full md:w-32 shrink-0">
            <div className="text-3xl font-serif text-plum-900/20">02</div>
            <div className="text-sm font-medium text-plum-900 mt-1">Documents</div>
          </div>

          <div className="flex-1 space-y-6">
            <div 
              onDragOver={onDragOver} onDragLeave={onDragLeave} onDrop={onDrop}
              className={cn("w-full border-2 border-dashed rounded-2xl p-10 flex flex-col items-center justify-center transition-colors text-center cursor-pointer", isDragging ? "border-coral-500 bg-coral-500/5" : "border-plum-900/15 bg-cream-50 hover:bg-cream-100 hover:border-plum-900/30")}
              onClick={() => inputRef.current?.click()}
            >
              <div className="w-12 h-12 rounded-full bg-white shadow-soft flex items-center justify-center mb-4 text-plum-900">
                <UploadCloud size={24} />
              </div>
              <p className="font-medium text-plum-900 mb-1">Drop your prescription or hospital bill here</p>
              <p className="text-sm text-text-secondary">or click to browse from your computer</p>
              <p className="text-xs text-text-secondary/70 mt-4">Accepted: JPG, PNG, PDF (Max 10MB)</p>
              <input ref={inputRef} id="document-upload" type="file" multiple accept=".pdf,.png,.jpg,.jpeg,.webp,application/pdf,image/png,image/jpeg,image/webp" onChange={event => addFiles(Array.from(event.target.files || []))} className="sr-only" />
            </div>
            
            {errors.documents && <div className="flex items-center gap-2 text-danger bg-danger/5 p-3 rounded-xl border border-danger/10"><AlertCircle size={16} /> <p className="text-sm">{errors.documents}</p></div>}

            {files.length > 0 && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {files.map(item => (
                  <div key={item.key} className="flex min-w-0 items-start justify-between gap-4 rounded-xl border border-plum-900/10 bg-white p-4 shadow-sm group">
                    <div className="flex min-w-0 items-start gap-3">
                      <div className="w-10 h-10 rounded-lg bg-cream-100 flex items-center justify-center text-plum-900 shrink-0">
                        <FileText size={20} />
                      </div>
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium text-plum-900" title={item.file.name}>{item.file.name}</p>
                        <p className="text-xs text-text-secondary mt-1">{fileType(item.file)} • {fileSize(item.file.size)}</p>
                        <div className="flex items-center gap-1 mt-1.5">
                          <div className={cn("w-1.5 h-1.5 rounded-full", item.status === "uploaded" ? "bg-success" : item.status === "uploading" ? "bg-info animate-pulse" : item.status === "failed" ? "bg-danger" : "bg-text-secondary/30")} />
                          <span className="text-[10px] font-medium text-text-secondary uppercase tracking-wider">
                            {item.status === "uploaded" ? "Uploaded" : item.status === "uploading" ? "Uploading…" : item.status === "failed" ? "Failed" : "Ready"}
                          </span>
                        </div>
                        {item.error && <p className="text-xs text-danger mt-1">{item.error}</p>}
                      </div>
                    </div>
                    <button type="button" onClick={(e) => { e.stopPropagation(); removeFile(item.key); }} disabled={item.status === "uploading"} aria-label={`Remove ${item.file.name}`} className="p-2 text-text-secondary hover:text-danger hover:bg-danger/5 rounded-lg transition-colors opacity-0 group-hover:opacity-100 disabled:opacity-50">
                      <Trash2 size={16} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>

        <hr className="border-plum-900/5" />

        {/* Optional Demo Setting */}
        <section className="flex flex-col md:flex-row gap-8">
          <div className="w-full md:w-32 shrink-0" />
          <div className="flex-1">
            <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-plum-900/10 bg-cream-50 p-4 hover:border-plum-900/20 transition-colors">
              <input type="checkbox" checked={form.simulateFailure} onChange={event => setField("simulateFailure", event.target.checked)} className="mt-1 accent-coral-500 w-4 h-4 rounded border-plum-900/20 text-coral-500 focus:ring-coral-500/20" />
              <div>
                <span className="block text-sm font-medium text-plum-900">Simulate Component Failure (Only check for Testcase 11(TC011) Demo)</span>
                <span className="text-sm text-text-secondary mt-0.5 block">Intentionally fail fraud analysis to demonstrate graceful degradation.</span>
              </div>
            </label>
          </div>
        </section>

        {/* Submit */}
        <div className="flex justify-end pt-6">
          <button type="submit" disabled={isLoading || isUploading} className={cn("flex items-center gap-2 rounded-full px-8 py-3 text-sm font-medium transition-all", isLoading || isUploading ? "cursor-not-allowed bg-cream-100 text-text-secondary" : "bg-coral-500 text-plum-900 hover:bg-coral-400 hover:-translate-y-0.5 shadow-soft hover:shadow-elevated")}>
            {isLoading ? "Processing Claim..." : isUploading ? "Uploading documents..." : "Submit Claim"}
          </button>
        </div>
      </form>
    </div>
  );
}
