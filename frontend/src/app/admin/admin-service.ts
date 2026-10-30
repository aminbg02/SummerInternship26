import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

import { API_BASE } from '../core/config';
import {
  AdminCompany,
  CompanyIsolation,
  QdrantPoolStatus,
  MovedUsers,
  AdminProvider,
  AdminPiiRule,
  DeleteKbResponse,
  Deletion,
  FeedbackSummary,
  IngestResponse,
  Ingestion,
  KbDocumentContent,
  UsageSummary,
} from '../core/models';

export interface ProviderPayload {
  display_name: string;
  provider_key: string;
  base_url: string | null;
  model_name: string;
  api_key?: string;
  enabled: boolean;
  is_free: boolean;
  rate_limit_rpm: number | null;
  rate_limit_rpd: number | null;
  priority: number;
  default_temperature: number | null;
  max_output_tokens: number | null;
}

export interface PiiRulePayload {
  entity_name: string;
  pattern: string;
  score: number;
  enabled: boolean;
  company_id: number | null;
}

export interface CreatePiiRulePayload {
  entity_name: string;
  pattern: string;
  score: number;
  enabled: boolean;
  company_ids: number[];
}

@Injectable({ providedIn: 'root' })
export class AdminService {
  private http = inject(HttpClient);
  private base = `${API_BASE}/admin/llm-providers`;

  listProviders(): Observable<{ providers: AdminProvider[] }> {
    return this.http.get<{ providers: AdminProvider[] }>(this.base);
  }

  createProvider(body: ProviderPayload): Observable<{ provider: AdminProvider }> {
    return this.http.post<{ provider: AdminProvider }>(this.base, body);
  }

  updateProvider(id: number, body: Partial<ProviderPayload>): Observable<{ provider: AdminProvider }> {
    return this.http.put<{ provider: AdminProvider }>(`${this.base}/${id}`, body);
  }

  deleteProvider(id: number): Observable<{ deleted: number }> {
    return this.http.delete<{ deleted: number }>(`${this.base}/${id}`);
  }

  testProvider(id: number): Observable<{ ok: boolean; result?: { content: string }; detail?: string }> {
    return this.http.post<{ ok: boolean; result?: { content: string }; detail?: string }>(
      `${this.base}/${id}/test`,
      {},
    );
  }

  listPiiRules(): Observable<{ rules: AdminPiiRule[] }> {
    return this.http.get<{ rules: AdminPiiRule[] }>(`${API_BASE}/admin/pii-rules`);
  }

  createPiiRule(body: CreatePiiRulePayload): Observable<{ rules: AdminPiiRule[] }> {
    return this.http.post<{ rules: AdminPiiRule[] }>(`${API_BASE}/admin/pii-rules`, body);
  }

  updatePiiRule(id: number, body: Partial<PiiRulePayload>): Observable<{ rule: AdminPiiRule }> {
    return this.http.put<{ rule: AdminPiiRule }>(`${API_BASE}/admin/pii-rules/${id}`, body);
  }

  deletePiiRule(id: number): Observable<{ deleted: number }> {
    return this.http.delete<{ deleted: number }>(`${API_BASE}/admin/pii-rules/${id}`);
  }

  getUsage(opts: { since?: string; company_id?: number; provider_id?: number } = {}): Observable<UsageSummary> {
    let params = new HttpParams();
    if (opts.since) params = params.set('since', opts.since);
    if (opts.company_id != null) params = params.set('company_id', String(opts.company_id));
    if (opts.provider_id != null) params = params.set('provider_id', String(opts.provider_id));
    return this.http.get<UsageSummary>(`${API_BASE}/admin/usage`, { params });
  }

  getFeedback(opts: { since?: string; company_id?: number; provider_id?: number } = {}): Observable<FeedbackSummary> {
    let params = new HttpParams();
    if (opts.since) params = params.set('since', opts.since);
    if (opts.company_id != null) params = params.set('company_id', String(opts.company_id));
    if (opts.provider_id != null) params = params.set('provider_id', String(opts.provider_id));
    return this.http.get<FeedbackSummary>(`${API_BASE}/admin/feedback`, { params });
  }

  listCompanies(): Observable<{ companies: AdminCompany[] }> {
    return this.http.get<{ companies: AdminCompany[] }>(`${API_BASE}/admin/companies`);
  }

  createCompany(body: {
    name: string;
    domain?: string | null;
    daily_token_limit?: number | null;
    daily_request_limit?: number | null;
    isolation?: CompanyIsolation;
  }): Observable<{ company: AdminCompany; warning?: string }> {
    return this.http.post<{ company: AdminCompany; warning?: string }>(
      `${API_BASE}/admin/companies`,
      body,
    );
  }

  qdrantPool(): Observable<QdrantPoolStatus> {
    return this.http.get<QdrantPoolStatus>(`${API_BASE}/admin/qdrant-pool`);
  }

  updateCompany(
    id: number,
    body: Partial<AdminCompany>,
  ): Observable<{ company: AdminCompany; users?: MovedUsers }> {
    return this.http.put<{ company: AdminCompany; users?: MovedUsers }>(
      `${API_BASE}/admin/companies/${id}`,
      body,
    );
  }

  ingest(companyId: number, file: File): Observable<IngestResponse> {
    const form = new FormData();
    form.append('file', file);
    return this.http.post<IngestResponse>(`${API_BASE}/documents/ingest`, form, {
      headers: { 'X-Company-Id': String(companyId) },
    });
  }

  ingestOwn(file: File): Observable<IngestResponse> {
    const form = new FormData();
    form.append('file', file);
    return this.http.post<IngestResponse>(`${API_BASE}/documents/ingest`, form);
  }

  listIngestions(companyId?: number): Observable<{ ingestions: Ingestion[] }> {
    let params = new HttpParams();
    if (companyId != null) params = params.set('company_id', String(companyId));
    return this.http.get<{ ingestions: Ingestion[] }>(`${API_BASE}/admin/ingestions`, { params });
  }

  deleteFromKb(companyId: number, documentId: number): Observable<DeleteKbResponse> {
    return this.http.delete<DeleteKbResponse>(`${API_BASE}/documents/kb/${documentId}`, {
      headers: { 'X-Company-Id': String(companyId) },
    });
  }

  listDeletions(companyId?: number): Observable<{ deletions: Deletion[] }> {
    let params = new HttpParams();
    if (companyId != null) params = params.set('company_id', String(companyId));
    return this.http.get<{ deletions: Deletion[] }>(`${API_BASE}/admin/deletions`, { params });
  }

  getKbDocumentContent(companyId: number, documentId: number): Observable<KbDocumentContent> {
    return this.http.get<KbDocumentContent>(
      `${API_BASE}/documents/kb/${documentId}/content`,
      { headers: { 'X-Company-Id': String(companyId) } },
    );
  }
}
