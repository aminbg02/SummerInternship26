import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { API_BASE } from './config';
import { AccountUsage } from './models';

@Injectable({ providedIn: 'root' })
export class AccountService {
  private http = inject(HttpClient);

  usage(): Observable<AccountUsage> {
    return this.http.get<AccountUsage>(`${API_BASE}/account/usage`);
  }
}
