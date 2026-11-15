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

export type ComplianceRun = {
  run_id: string;
  filename: string;
  status: "ready" | "running" | "done" | "cancelled" | "error";
  progress: number;
  total: number;
  model: string;
  standards: { id: number; title: string; collection: string; pages: number; status: string }[];
  extra_columns: string[];
  instructions: string;
  clauses: ComplianceClause[];
  results: ComplianceResult[];
  error: string;
};

export type StandardDocument = {
  id: number;
  title: string;
  collection: string;
  pages: number;
  status: string;
};
