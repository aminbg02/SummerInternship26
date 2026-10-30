export type Role = 'customer' | 'company_admin' | 'super_admin';

export interface User {
  id: number;
  email: string;
  role: Role;
  company_id: number | null;
}

export interface QuotaSnapshot {
  used: number;
  limit: number | null;
  remaining: number | null;
  percent: number;
  name?: string;
}

export interface AccountUsage extends QuotaSnapshot {
  user_id: number;
  role: Role;
  company_id: number | null;
  scope?: 'user' | 'company';
  blocked_by?: boolean;
  user?: QuotaSnapshot;
  company?: QuotaSnapshot | null;
}

export interface ManagedUser {
  id: number;
  email: string;
  role: Role;
  company_id: number | null;
  daily_token_limit: number | null;
  effective_token_limit: number;
  created_at: string | null;
}

export interface TokenRequest {
  id: number;
  requester_id: number;
  requester_email: string | null;
  company_id: number;
  company_name: string | null;
  scope: 'user' | 'company';
  requested_limit: number;
  reason: string;
  status: 'pending' | 'approved' | 'rejected';
  decision_reason: string | null;
  reviewed_by: number | null;
  reviewed_by_email: string | null;
  reviewed_at: string | null;
  created_at: string | null;
}

export interface LoginResponse {
  access_token: string;
  user: User;
}

export interface Provider {
  id: number;
  display_name: string;
  model_name: string;
  is_free: boolean;
  default_temperature: number | null;
  max_output_tokens: number | null;
  available?: boolean;
  reason?: string | null;
  retry_after?: number | null;
}

export interface ProviderView extends Provider {
  available: boolean;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  id?: number;
  provider?: string;
  usage?: Usage;
  params?: AppliedParams;
  fellBack?: boolean;
  sources?: Chunk[];
  citations?: Citation[];
  feedback?: 'up' | 'down' | null;
  error?: boolean;
}

export interface Citation {
  document_id: number | null;
  filename: string;
  score: number;
}

export interface AppliedParams {
  temperature: number;
  max_tokens: number;
}

export interface Chunk {
  id: string;
  score: number;
  text: string;
  category: string;
  redacted: boolean;
  payload: Record<string, unknown>;
}

export interface Usage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
}

export interface QueryResponse {
  company_id: number;
  question: string;
  chunks: Chunk[];
  count: number;
  blocked: number;
  answer?: string;
  provider?: string;
  provider_id?: number;
  conversation_id?: number;
  message_id?: number;
  sources?: Citation[];
  usage?: Usage;
  params?: AppliedParams;
  fell_back?: boolean;
  requested_provider_id?: number;
}

export interface AdminProvider {
  id: number;
  display_name: string;
  provider_key: string;
  base_url: string | null;
  model_name: string;
  enabled: boolean;
  is_free: boolean;
  rate_limit_rpm: number | null;
  rate_limit_rpd: number | null;
  priority: number;
  default_temperature: number | null;
  max_output_tokens: number | null;
  company_id: number | null;
  has_api_key: boolean;
  created_at: string | null;
}

export interface AdminPiiRule {
  id: number;
  entity_name: string;
  pattern: string;
  score: number;
  enabled: boolean;
  company_id: number | null;
  created_at: string | null;
}

export interface UsageTotal {
  prompt_tokens: number;
  completion_tokens: number;
  reasoning_tokens: number;
  total_tokens: number;
  requests: number;
}

export interface UsageRow extends UsageTotal {
  id: number | null;
  name: string;
}

export interface UsageDay extends UsageTotal {
  day: string;
}

export interface UsageSummary {
  total: UsageTotal;
  by_company: UsageRow[];
  by_provider: UsageRow[];
  by_user: UsageRow[];
  by_day: UsageDay[];
}

export interface FeedbackTotal {
  up: number;
  down: number;
  rated: number;
  answers: number;
  score: number | null;
}

export interface FeedbackRow extends FeedbackTotal {
  id: number | null;
  name: string;
}

export interface FeedbackReviewItem {
  message_id: number;
  conversation_id: number;
  company_id: number | null;
  company_name: string;
  provider_id: number | null;
  provider_name: string;
  content: string;
  sources: Citation[];
  created_at: string | null;
}

export interface FeedbackSummary {
  total: FeedbackTotal;
  by_provider: FeedbackRow[];
  by_company: FeedbackRow[];
  review: FeedbackReviewItem[];
}

export type CompanyIsolation = 'shared' | 'dedicated';

export interface AdminCompany {
  id: number;
  name: string;
  domain?: string | null;
  daily_token_limit?: number | null;
  daily_request_limit?: number | null;
  isolation?: CompanyIsolation;
  qdrant_url?: string | null;
}

export interface QdrantPoolSlot {
  url: string;
  claimed_by: { company_id: number; company_name: string } | null;
}

export interface QdrantPoolStatus {
  configured: number;
  free: number;
  available: boolean;
  slots: QdrantPoolSlot[];
}

export interface MovedUsers {
  moved: { from: string; to: string }[];
  skipped: { email: string; reason: string }[];
}

export interface Ingestion {
  id: number;
  company_id: number;
  document_id: number | null;
  user_id: number | null;
  filename: string;
  chunks_indexed: number;
  chunks_blocked: number;
  created_at: string | null;
}

export interface IngestResponse {
  document_id: number;
  filename: string;
  scope: string;
  company_id: number;
  chunks_indexed: number;
  chunks_blocked: number;
  categories: string[];
}

export interface Deletion {
  id: number;
  company_id: number;
  document_id: number | null;
  user_id: number | null;
  filename: string;
  chunks_deleted: number;
  created_at: string | null;
}

export interface DeleteKbResponse {
  document_id: number;
  filename: string;
  company_id: number;
  chunks_deleted: number;
}

export interface KbChunk {
  id: string;
  text: string;
}

export interface KbDocumentContent {
  document_id: number;
  filename: string;
  company_id: number;
  chunks: KbChunk[];
}

export interface UploadResponse {
  document_id: number;
  filename: string;
  scope: string;
  conversation_id: number | null;
  accepted_chunks: number;
  blocked_chunks: number;
  redacted_chunks: number;
  categories: string[];
  staged_chunk_ids: number[];
}

export interface ConversationSummary {
  id: number;
  title: string;
  created_at: string;
  last_at: string;
  message_count: number;
}

export interface StoredMessage {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  sources?: Citation[];
  feedback?: 'up' | 'down' | null;
  created_at: string;
}
