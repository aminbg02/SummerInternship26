import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { API_BASE } from './config';
import { ManagedUser, Role } from './models';

export interface CreateUserPayload {
  email: string;
  password: string;
  role?: Role;
  daily_token_limit?: number | null;
}

@Injectable({ providedIn: 'root' })
export class UsersService {
  private http = inject(HttpClient);
  private base = `${API_BASE}/users`;

  listUsers(): Observable<{
    users: ManagedUser[];
    company_limits: Record<string, number | null>;
    company_allocated: Record<string, number>;
  }> {
    return this.http.get<{
      users: ManagedUser[];
      company_limits: Record<string, number | null>;
      company_allocated: Record<string, number>;
    }>(this.base);
  }

  setTokenLimit(id: number, limit: number | null): Observable<{ user: ManagedUser }> {
    return this.http.patch<{ user: ManagedUser }>(`${this.base}/${id}/token-limit`, {
      daily_token_limit: limit,
    });
  }

  createUser(body: CreateUserPayload): Observable<{ user: ManagedUser }> {
    return this.http.post<{ user: ManagedUser }>(this.base, body);
  }

  deleteUser(id: number): Observable<{ deleted: number }> {
    return this.http.delete<{ deleted: number }>(`${this.base}/${id}`);
  }
}
