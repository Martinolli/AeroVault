export type LibraryDocument = {
  id: number;
  title: string;
  collection: string;
  pages: number;
  status: string;
  vectors: number;
};

export type Source = {
  n: number;
  tag: string;
  document_id: number;
  title: string;
  collection: string;
  page: number;
  excerpt: string;
};

export type ChatMessage = {
  id?: number;
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
};

export type ChatSummary = {
  id: number;
  title: string;
  model: string;
  created_at: string;
  updated_at: string;
  messages: number;
};

export type ChatDetail = {
  id: number;
  title: string;
  model: string;
  created_at: string;
  updated_at: string;
  messages: ChatMessage[];
};

export type ViewerTarget = {
  documentId: number;
  title: string;
  page: number;
  excerpt?: string;
};

export type ComplianceClause = {
  id: string;
  heading: string;
  text: string;
};

export type ComplianceResult = {
  clause_id: string;
  clause_heading: string;
  clause_excerpt: string;
  status: "Compliant" | "Partial" | "Gap" | "Not applicable" | "Unclear";
  requirement: string;
  standard: string;
  standard_clause: string;
  page: number;
  document_id: number;
  evidence: string;
  rationale: string;
  action: string;
  confidence: "High" | "Medium" | "Low";
  extras: Record<string, string>;
};

export type ComplianceMode = "problem" | "gap" | "improvement";

export type ComplianceNarrative = {
  problem_understanding: string;
  applicable_requirements: {
    requirement: string;
    authority: string;
    document: string;
    document_id?: number;
    clause: string;
    page: number;
    citation_verified?: boolean;
    evidence: string;
    relevance: string;
  }[];
  procedure_evidence: {
    finding: string;
    document: string;
    clause: string;
    page?: number;
    citation_verified?: boolean;
    evidence: string;
  }[];
  gaps_or_conflicts: {
    issue: string;
    why_it_matters: string;
    severity: string;
    evidence: string;
  }[];
  contributing_factors: {
    factor: string;
    explanation: string;
    confidence: string;
  }[];
  risk_assessment: {
    likelihood: string;
    severity: string;
    risk_level: string;
    rationale: string;
  };
  corrective_actions: {
    action: string;
    owner: string;
    priority: string;
    verification: string;
  }[];
  verification: string;
  limitations: string;
  citations: {
    ref: string;
    document: string;
    collection: string;
    document_id: number;
    page: number;
  }[];
};

export type ComplianceRun = {
  run_id: string;
  filename: string;
  document_id: number | null;
  mode: ComplianceMode;
  problem_brief: string;
  authorities: string[];
  status: "ready" | "running" | "done" | "cancelled" | "error";
  progress: number;
  total: number;
  model: string;
  standards: { id: number; title: string; collection: string; pages: number; status: string }[];
  extra_columns: string[];
  instructions: string;
  clauses: ComplianceClause[];
  results: ComplianceResult[];
  narrative: ComplianceNarrative | Record<string, never>;
  error: string;
};

export type ComplianceHistoryItem = {
  run_id: string;
  filename: string;
  document_id: number | null;
  mode: ComplianceMode;
  created_at: string;
  expires_at: string;
  model: string;
  standards: { id: number; title: string; collection: string }[];
  authorities: string[];
  status: string;
  progress: number;
  total: number;
  error: string;
};

export type StandardDocument = {
  id: number;
  title: string;
  collection: string;
  pages: number;
  status: string;
};
