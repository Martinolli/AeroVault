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
