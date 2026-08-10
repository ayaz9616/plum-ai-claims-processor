"use client";

import { CheckCircle2, XCircle, AlertTriangle } from "lucide-react";
import { formatCurrency, formatPercentage } from "../app/utils";

type RecordValue = Record<string, unknown>;

const LABELS: Record<string, string> = {
  member_id: "Member ID", member_name: "Member", member_found: "Member Found",
  policy_id: "Policy", policy_valid: "Policy Valid", document_type: "Document Type",
  file_id: "Document", treatment_date: "Treatment Date", confidence: "Confidence",
  confidence_score: "Confidence", line_item_total: "Itemized Total", amount_payable: "Amount Payable",
  amount_received: "Amount Received", grand_total: "Grand Total", review_required: "Manual Review Required",
  required: "Required Documents", provided: "Provided Documents", missing: "Missing", unreadable: "Unreadable",
  wrong_type: "Wrong Document Type", found_names: "Patient Names", mismatches: "Issues",
  eligible: "Eligible", status: "Status", message: "Result", checks: "Policy Checks", signals: "Signals", approved: "Calculated Reimbursable Amount",
  copay_percent: "Co-pay", network_discount_percent: "Network Discount", sub_limit: "Sub-limit",
  pre_authorization_required: "Pre-authorization Required", is_network: "Network Status", hospital_name: "Hospital",
};

const MONEY = /(^|_)(amount|total|subtotal|tax|discount|copay|approved|claimed|reimbursable)(_|$)/;
const PERCENT = /(^|_)(percent|pct|confidence|confidence_score)$/;

export function formatLabel(key: string) {
  return LABELS[key] || key.replace(/_/g, " ").replace(/\b\w/g, char => char.toUpperCase());
}

function formatDate(value: string) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return value;
  const date = new Date(`${value}T00:00:00`);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat("en-IN", { day: "2-digit", month: "short", year: "numeric" }).format(date);
}

export function formatValue(key: string, value: unknown): string {
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (value === null || value === undefined || value === "") return "None";
  if (typeof value === "number" || (typeof value === "string" && (MONEY.test(key) || PERCENT.test(key)) && !Number.isNaN(Number(value)))) {
    if (PERCENT.test(key)) return formatPercentage(value);
    if (MONEY.test(key)) return formatCurrency(value);
  }
  if (typeof value === "string") return key.includes("date") ? formatDate(value) : value.replace(/_/g, " ");
  return String(value);
}

function StatusValue({ value }: { value: boolean }) {
  return value ? <span className="inline-flex items-center gap-1 text-emerald-700"><CheckCircle2 className="h-3.5 w-3.5" />Yes</span> : <span className="inline-flex items-center gap-1 text-rose-700"><XCircle className="h-3.5 w-3.5" />No</span>;
}

function LineItems({ items }: { items: unknown[] }) {
  if (items.length === 0) return <span>None</span>;
  return <ul className="space-y-1">{items.map((item, index) => {
    if (typeof item === "string") return <li key={index}>• {formatValue("", item)}</li>;
    if (item && typeof item === "object") {
      const row = item as RecordValue;
      if ("description" in row) return <li key={index}>• {String(row.description)}{row.amount !== undefined ? ` — ${formatValue("amount", row.amount)}` : ""}</li>;
      if ("name" in row) return <li key={index}>• {String(row.name)}{row.relationship ? ` — ${formatValue("relationship", row.relationship)}` : ""}</li>;
      return <li key={index}><StructuredEvidence value={row} compact /></li>;
    }
    return <li key={index}>• {formatValue("", item)}</li>;
  })}</ul>;
}

function PolicyChecks({ checks }: { checks: unknown[] }) {
  return <div className="space-y-2">{checks.map((check, index) => {
    const row = check as RecordValue;
    const ok = Boolean(row.ok);
    const details = row.details as RecordValue | undefined;
    return <div className="rounded-md border border-slate-100 bg-slate-50 px-2.5 py-2" key={index}>
      <div className="flex gap-1.5 text-xs font-semibold text-slate-800">{ok ? <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 shrink-0" /> : <AlertTriangle className="h-3.5 w-3.5 text-amber-600 shrink-0" />}{formatLabel(String(row.name || "policy check"))}</div>
      {details && <div className="mt-1 text-xs text-slate-600"><StructuredEvidence value={details} compact /></div>}
    </div>;
  })}</div>;
}

export function StructuredEvidence({ value, compact = false }: { value: unknown; compact?: boolean }) {
  if (Array.isArray(value)) return <LineItems items={value} />;
  if (!value || typeof value !== "object") return <span>{formatValue("", value)}</span>;
  const object = value as RecordValue;
  if (Array.isArray(object.checks)) return <PolicyChecks checks={object.checks} />;
  if (Object.keys(object).length === 0) return <span>None</span>;
  return <dl className={compact ? "space-y-1" : "grid grid-cols-1 gap-x-3 gap-y-2 sm:grid-cols-2"}>
    {Object.entries(object).map(([key, item]) => {
      if (key === "file_id") return null;
      if (key === "found_names" && Array.isArray(item) && new Set(item.filter((name): name is string => typeof name === "string").map(name => name.toLowerCase().replace(/[^a-z0-9]/g, ""))).size <= 1) return <div key={key}><dt className="text-[11px] font-medium uppercase tracking-wide text-slate-500">Patient Identity</dt><dd className="mt-0.5 text-xs text-emerald-700">✓ Identity matched — patient identity matches after normalization.</dd></div>;
      return <div key={key} className={Array.isArray(item) || (item && typeof item === "object") ? "sm:col-span-2" : ""}>
        <dt className="text-[11px] font-medium uppercase tracking-wide text-slate-500">{formatLabel(key)}</dt>
        <dd className="mt-0.5 break-words text-xs text-slate-700">{typeof item === "boolean" ? <StatusValue value={item} /> : (item && typeof item === "object" ? <StructuredEvidence value={item} compact /> : formatValue(key, item))}</dd>
      </div>;
    })}
  </dl>;
}
