export type DocumentArtifact = {
  file_id: string;
  file_name?: string;
  mime_type?: string;
  size_bytes?: number;
  actual_type?: string;
  content?: Record<string, any>;
};

export type ClaimSubmission = {
  member_id: string;
  policy_id: string;
  claim_category: string;
  treatment_date: string;
  claimed_amount: number;
  simulate_component_failure?: boolean;
  documents: DocumentArtifact[];
};

export type TraceEvent = {
  trace_id: string;
  claim_id?: string;
  step: string;
  component: string;
  status: string;
  duration_ms?: number;
  safe_input?: any;
  safe_output?: any;
  evidence?: any;
  error?: string;
  summary?: string;
  reason_code?: string;
};

export type RuleResult = {
  name: string;
  ok: boolean;
  details?: Record<string, any>;
};

export type PolicyEvaluation = {
  policy_id: string;
  checks: RuleResult[];
};

export type ClaimProcessingResult = {
  claim_id: string;
  decision?: string;
  approved_amount?: number;
  reimbursable_amount?: number;
  confidence_score?: number;
  processing_status: string;
  decision_summary?: string;
  degraded: boolean;
  manual_review_recommended: boolean;
  component_failures: Array<Record<string, any>>;
  trace: TraceEvent[];
};
