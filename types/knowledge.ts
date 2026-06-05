export interface KnowledgeEntry {
  id: string;
  title: string;
  content: string;
  sourceFileName: string;
  sourceType: string;
  tags: string[];
  createdAt: string;
  updatedAt: string;
}

export type KnowledgeEntryInput = Omit<KnowledgeEntry, "id" | "createdAt" | "updatedAt">;

export interface KnowledgeFilters {
  sourceType?: string;
  tag?: string;
  search?: string;
}
