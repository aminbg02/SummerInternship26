import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { API_BASE } from '../../core/config';
import {
  ConversationSummary,
  Provider,
  QueryResponse,
  StoredMessage,
  UploadResponse,
} from '../../core/models';

@Injectable({ providedIn: 'root' })
export class ChatService {
  private http = inject(HttpClient);

  private tenantHeaders(companyId?: number | null) {
    return companyId != null ? { 'X-Company-Id': String(companyId) } : undefined;
  }

  listProviders(): Observable<{ providers: Provider[] }> {
    return this.http.get<{ providers: Provider[] }>(`${API_BASE}/llm-providers`);
  }

  sendQuery(
    body: {
      question: string;
      provider_id?: number;
      conversation_id?: number;
      temperature?: number;
      max_tokens?: number;
      locale?: string;
    },
    companyId?: number | null,
  ): Observable<QueryResponse> {
    return this.http.post<QueryResponse>(`${API_BASE}/query`, body, {
      headers: this.tenantHeaders(companyId),
    });
  }

  listConversations(companyId?: number | null): Observable<{ conversations: ConversationSummary[] }> {
    return this.http.get<{ conversations: ConversationSummary[] }>(`${API_BASE}/conversations`, {
      headers: this.tenantHeaders(companyId),
    });
  }

  getConversation(
    id: number,
    companyId?: number | null,
  ): Observable<{ conversation: ConversationSummary; messages: StoredMessage[] }> {
    return this.http.get<{ conversation: ConversationSummary; messages: StoredMessage[] }>(
      `${API_BASE}/conversations/${id}`,
      { headers: this.tenantHeaders(companyId) },
    );
  }

  renameConversation(
    id: number,
    title: string,
    companyId?: number | null,
  ): Observable<{ conversation: ConversationSummary }> {
    return this.http.patch<{ conversation: ConversationSummary }>(
      `${API_BASE}/conversations/${id}`,
      { title },
      { headers: this.tenantHeaders(companyId) },
    );
  }

  setFeedback(
    conversationId: number,
    messageId: number,
    value: 'up' | 'down' | null,
    companyId?: number | null,
  ): Observable<{ message_id: number; feedback: 'up' | 'down' | null }> {
    return this.http.post<{ message_id: number; feedback: 'up' | 'down' | null }>(
      `${API_BASE}/conversations/${conversationId}/messages/${messageId}/feedback`,
      { value },
      { headers: this.tenantHeaders(companyId) },
    );
  }

  deleteConversation(id: number, companyId?: number | null): Observable<{ deleted: number }> {
    return this.http.delete<{ deleted: number }>(`${API_BASE}/conversations/${id}`, {
      headers: this.tenantHeaders(companyId),
    });
  }

  upload(
    file: File,
    conversationId: number | null,
    companyId?: number | null,
  ): Observable<UploadResponse> {
    const form = new FormData();
    form.append('file', file);
    if (conversationId != null) {
      form.append('conversation_id', String(conversationId));
    }
    return this.http.post<UploadResponse>(`${API_BASE}/documents/upload`, form, {
      headers: this.tenantHeaders(companyId),
    });
  }
}
