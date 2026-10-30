import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';

import { UsageRow, UsageSummary } from '../../core/models';
import { LanguageService } from '../../core/language';
import { AdminService } from '../admin-service';

@Component({
  selector: 'app-usage-admin',
  imports: [FormsModule, DecimalPipe],
  templateUrl: './usage.html',
  styleUrl: './usage.css',
})
export class UsageAdmin implements OnInit {
  private admin = inject(AdminService);
  readonly lang = inject(LanguageService);

  readonly summary = signal<UsageSummary | null>(null);
  readonly error = signal<string | null>(null);

  sinceDays: number | null = null;

  readonly maxCompanyTokens = computed(() => this.maxOf(this.summary()?.by_company));
  readonly maxProviderTokens = computed(() => this.maxOf(this.summary()?.by_provider));
  readonly maxUserTokens = computed(() => this.maxOf(this.summary()?.by_user));

  readonly maxDayTokens = computed(() => {
    const rows = this.summary()?.by_day;
    if (!rows || rows.length === 0) return 1;
    return Math.max(1, ...rows.map((r) => r.total_tokens));
  });

  readonly avgTokensPerRequest = computed(() => {
    const t = this.summary()?.total;
    return t && t.requests > 0 ? Math.round(t.total_tokens / t.requests) : 0;
  });

  private maxOf(rows: UsageRow[] | undefined): number {
    if (!rows || rows.length === 0) return 1;
    return Math.max(1, ...rows.map((r) => r.total_tokens));
  }

  barWidth(value: number, max: number): number {
    return Math.max(2, Math.round((value / max) * 100));
  }

  dayLabel(day: string): string {
    const [, m, d] = day.split('-');
    return d && m ? `${d}/${m}` : day;
  }

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    const days = this.sinceDays;
    const since = days != null && days > 0 ? String(Math.floor(days)) : undefined;
    this.admin.getUsage({ since }).subscribe({
      next: (s) => {
        this.summary.set(s);
        this.error.set(null);
      },
      error: () => this.error.set('Failed to load usage.'),
    });
  }
}
