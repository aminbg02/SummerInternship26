import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { API_BASE } from './config';
import { TokenRequest } from './models';

@Injectable({ providedIn: 'root' })
export class TokenRequestsService {
  private http = inject(HttpClient);
  private base = `${API_BASE}/token-requests`;

  list(): Observable<{ requests: TokenRequest[] }> {
    return this.http.get<{ requests: TokenRequest[] }>(this.base);
  }

  create(body: { requested_limit: number; reason: string }): Observable<{ request: TokenRequest }> {
    return this.http.post<{ request: TokenRequest }>(this.base, body);
  }

  decide(
    id: number,
    body: { status: 'approved' | 'rejected'; decision_reason?: string },
  ): Observable<{ request: TokenRequest }> {
    return this.http.patch<{ request: TokenRequest }>(`${this.base}/${id}`, body);
  }
}
